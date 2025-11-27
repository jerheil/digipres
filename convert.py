import csv
import os
import subprocess
import tkinter as tk
from tkinter import filedialog
from datetime import datetime

def select_folder_dialog(title="Select folder"):
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title=title)
    root.destroy()
    return folder_selected

def find_exiftool_executable():
    """
    Try to find an exiftool executable. Prefer 'exiftool' on PATH, otherwise fall back to common Windows path.
    Returns the executable path or raises FileNotFoundError.
    """
    # First try simple name (works if in PATH)
    for candidate in ("exiftool", "exiftool.exe"):
        try:
            subprocess.run([candidate, "-ver"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            return candidate
        except Exception:
            pass

    # Common Windows install location
    win_path = r"C:\Windows\exiftool.exe"
    if os.path.exists(win_path):
        return win_path

    raise FileNotFoundError("exiftool executable not found. Please install exiftool or ensure it's on your PATH.")

def run_exiftool_and_create_metadataexp(dest_folder, source_folder, output_name="metadataExp.csv"):
    """
    Run exiftool on source_folder recursively and write a CSV to dest_folder/output_name.
    Fields selected mirror the fields expected by the rest of this script.
    """
    try:
        exiftool = find_exiftool_executable()
    except FileNotFoundError as e:
        raise

    output_csv = os.path.join(dest_folder, output_name)
    args = [
        exiftool,
        "-csv", "-r",
        "-SourceFile", "-Title", "-FileName", "-FileCreateDate", "-FileModifyDate", "-PageCount",
        "-FileTypeExtension", "-MIMEType", "-LayerCount",
        "*"
    ]
    # Run exiftool with cwd=source_folder and capture stdout to the file
    with open(output_csv, "w", encoding="utf-8", newline='') as outfile:
        subprocess.run(args, cwd=source_folder, stdout=outfile, check=True)
    return output_csv

def convert_colons_to_hyphens(date):
    return date.replace(':', '-')

def remove_text_from_date(date):
    return date.split()[0]

def add_page_count_extension(page_count, extension):
    """
    - If extension is a photographic type, return "1 photograph ({extension})"
    - Else if there is no page_count (empty or falsy), return "1 digital file ({extension})"
    - Else return "{page_count} p. ({extension})"
    """
    extension = (extension or "").lower()
    photo_exts = ["psd", "jpg", "jpeg", "tif", "tiff", "png"]
    if extension in photo_exts:
        return f"1 photograph ({extension})"
    # No page count provided
    if not page_count or str(page_count).strip() == "":
        return f"1 digital file ({extension})" if extension else "1 digital file"
    # Otherwise use the page count
    return f"{page_count} p. ({extension})" if extension else f"{page_count} p."

def add_data_objects_prefix(source_file):
    return "data/objects/" + source_file

def process_layer_count(layer_count, extension, title, filename):
    """
    - If layer_count is numeric: increment and report as Photoshop file with X layers (as before)
    - Otherwise: return "Item is a ({extension}) file relating to {label}"
      where label is Title (if present) else FileName (without its extension).
    """
    # Normalize inputs
    layer_count_str = str(layer_count or "")
    extension = extension or ""
    title = title or ""
    filename = filename or ""

    # If numeric, keep previous behavior (report number of layers + 1)
    if layer_count_str.isdigit():
        layer_count_num = int(layer_count_str)
        new_layer_count = layer_count_num + 1
        if layer_count_num > 1:
            return f"Item is a Photoshop file with {new_layer_count} layers."
        else:
            return f"Item is a Photoshop file with {new_layer_count} layer."

    # Not numeric: build the "relating to" label from Title or FileName (without extension)
    label = ""
    if title.strip() and title.strip().upper() != "NULL":
        label = title.strip()
    elif filename.strip():
        # Use basename then strip extension
        base = os.path.basename(filename.strip())
        label = os.path.splitext(base)[0]
    else:
        label = ""

    if extension:
        return f"Item is a {extension} file relating to {label}" if label else f"Item is a {extension} file."
    else:
        return f"Item is a file relating to {label}" if label else "Item is a file."

def modify_row(row):
    # defensive: if keys missing, ensure defaults to empty strings
    row['FileCreateDate'] = row.get('FileCreateDate', '')
    row['FileCreateDate'] = convert_colons_to_hyphens(row['FileCreateDate'])
    row['FileCreateDate'] = remove_text_from_date(row['FileCreateDate'])
    row['SourceFile'] = add_data_objects_prefix(row.get('SourceFile', ''))
    row['PageCount'] = add_page_count_extension(row.get('PageCount', ''), row.get('FileTypeExtension', ''))
    # pass extension, Title and FileName to process_layer_count so it can produce the requested phrasing
    row['LayerCount'] = process_layer_count(row.get('LayerCount', ''), row.get('FileTypeExtension', ''), row.get('Title', ''), row.get('FileName', ''))
    return row

def delete_columns(row):
    # Use .pop with default to avoid KeyError if missing
    row.pop("Title", None)
    row.pop("FileTypeExtension", None)
    return row

def rename_columns(row):
    column_mapping = {
        "SourceFile": "filename",
        "FileName": "dc.title",
        "FileCreateDate": "dc.date",
        "PageCount": "dc.format",
        "MIMEType": "dc.format2",
        "LayerCount": "dc.description"
    }
    renamed_row = {column_mapping.get(key, key): value for key, value in row.items()}
    return renamed_row

def check_and_add_columns(rows):
    if not rows:
        return [], rows
    fieldnames = list(rows[0].keys())
    if "PageCount" not in fieldnames:
        fieldnames = fieldnames + ["PageCount"]
    if "LayerCount" not in fieldnames:
        fieldnames = fieldnames + ["LayerCount"]
    if "Title" not in fieldnames:
        fieldnames = fieldnames + ["Title"]
    return fieldnames, rows

def add_missing_columns(input_file):
    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            rows = list(reader)

        if not rows:
            print(f"No rows found in '{input_file}'. Nothing to add.")
            return

        fieldnames, _ = check_and_add_columns(rows)

        with open(input_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Added missing columns to '{input_file}'.")
    except Exception as e:
        print(f"An error occurred while adding missing columns: {e}")

def process_csv(input_file, output_file):
    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            rows = list(reader)

        modified_rows = []

        for row in rows:
            row = modify_row(row)
            row = delete_columns(row)
            row = rename_columns(row)
            modified_rows.append(row)

        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            fieldnames_mapping = {
                "filename": "filename",  # Adjust the column name here
                "dc.title": "dc.title",
                "dc.date": "dc.date",
                "dc.format": "dc.format",
                "dc.format2": "dc.format2",
                "dc.description": "dc.description"
            }
            writer = csv.DictWriter(outfile, fieldnames=fieldnames_mapping.values())
            writer.writeheader()

            for row in modified_rows:
                renamed_row = {fieldnames_mapping.get(key, key): value for key, value in row.items()}
                writer.writerow(renamed_row)

        print(f"Processing complete. Modified data written to '{output_file}'.")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_rights_csv():
    try:
        rights_file = "rights.csv"

        with open("metadataTmp.csv", 'r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            rows = list(reader)

        # Gather user input once
        doc_id_type = input("Enter 'u' for University Records Transfer or 'd' for Deed of Gift: ").strip().lower()
        doc_id_value = input("Enter a document ID value in the format ####-###: ").strip()

        # Map doc_id_type input to the corresponding value
        doc_id_type_mapping = {
            "d": "Deed of Gift",
            "u": "University Records Transfer"
        }

        with open(rights_file, 'w', newline='', encoding='utf-8') as outfile:
            fieldnames = ["file", "basis", "status", "determination_date", "jurisdiction", "start_date", "end_date",
                          "note", "grant_act", "grant_restriction", "grant_start_date", "grant_end_date",
                          "grant_note", "doc_id_type", "doc_id_value", "doc_id_role"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in rows:
                start_date = row.get("dc.date", "")
                if start_date:
                    start_date = start_date.split()[0]

                grant_start_date = datetime.today().strftime("%Y-%m-%d")

                new_row = {
                    "file": row.get("filename", ""),
                    "basis": "copyright",
                    "status": "copyrighted",
                    "determination_date": datetime.today().strftime("%Y-%m-%d"),
                    "jurisdiction": "ca",
                    "start_date": start_date,
                    "end_date": f"{int(start_date[:4]) + 100}-" + start_date[5:] if start_date else "",
                    "note": "Copyright held by creator",
                    "grant_act": "disseminate",
                    "grant_restriction": "Conditional",
                    "grant_start_date": grant_start_date,
                    "grant_end_date": f"{int(grant_start_date[:4]) + 100}-" + grant_start_date[5:],
                    "grant_note": "May disseminate with the permission of the creator.",
                    "doc_id_type": doc_id_type_mapping.get(doc_id_type, ""),
                    "doc_id_value": doc_id_value,
                    "doc_id_role": "Copyright held by creator"
                }
                writer.writerow(new_row)

        print(f"Rights data written to '{rights_file}'.")
    except Exception as e:
        print(f"An error occurred while creating rights.csv: {e}")

if __name__ == "__main__":
    # The script can optionally run exiftool to create metadataExp.csv before continuing.
    print("Do you want to generate metadataExp.csv by running exiftool on a folder of files? (y/n)")
    answer = input().strip().lower()
    if answer == "y":
        print("Please select the folder that contains the files to scan with exiftool.")
        source_folder = select_folder_dialog("Select source folder for exiftool")
        if not source_folder:
            print("No source folder selected. Exiting.")
            exit(1)
        print("Please select the destination folder where metadataExp.csv should be created.")
        dest_folder = select_folder_dialog("Select destination folder for metadataExp.csv")
        if not dest_folder:
            print("No destination folder selected. Exiting.")
            exit(1)
        try:
            generated = run_exiftool_and_create_metadataexp(dest_folder, source_folder, output_name="metadataExp.csv")
            print(f"metadataExp.csv generated at: {generated}")
        except FileNotFoundError as fnf:
            print(fnf)
            print("Cannot proceed without exiftool. Exiting.")
            exit(1)
        except subprocess.CalledProcessError as cpe:
            print(f"exiftool failed: {cpe}")
            exit(1)
        # Use generated file as input
        input_csv = os.path.join(dest_folder, "metadataExp.csv")
    else:
        input_csv = "metadataExp.csv"
        if not os.path.exists(input_csv):
            print(f"'{input_csv}' not found. You can generate it by answering 'y' when prompted next time.")
            exit(1)

    output_csv = "metadataTmp.csv"

    # Add missing columns if necessary
    add_missing_columns(input_csv)

    process_csv(input_csv, output_csv)

    # The second set of subroutines (kept largely as in original file)
    def add_objects_row(rows):
        new_row = ['objects'] + [''] * (len(rows[0]) - 1)
        rows.insert(1, new_row)

    def copy_filename_to_filename2(rows):
        for row in rows[1:]:
            filename = row[0]
            last_slash_index = filename.rfind('/')
            if last_slash_index != -1:
                row.append(filename[:last_slash_index])
            else:
                row.append('')

    def add_rows_above_unique_data(rows, unique_data):
        for unique_value in set(row[-1] for row in rows[1:] if row[-1] != 'filename2'):
            new_row = [unique_value] + [''] * (len(rows[0]) - 1)
            for i, row in enumerate(rows):
                if row[-1] == unique_value:
                    rows.insert(i, new_row)
                    break

    def delete_rows_and_columns(rows):
        # Note: original code deleted rows[1:2] # Delete rows 2 and 3 (this is effectively deleting only row index 1)
        # We'll keep the original intent (delete second row) but guard against IndexError
        if len(rows) > 1:
            del rows[1:2]
        for row in rows[1:]:
            if len(row) > 1 and not row[1]:  # If dc.title is blank
                row[0] = row[0].replace('data/', '')  # Delete "data/" from filename
        for row in rows:
            if row:
                del row[-1]  # Delete filename2 column

    def delete_first_row(rows):
        if rows:
            del rows[0]  # Delete the first row

    def process_csv_second_stage(input_file, output_file):
        try:
            with open(input_file, 'r', newline='', encoding='utf-8') as infile:
                reader = csv.reader(infile)
                rows = list(reader)
                if not rows:
                    print(f"No rows in {input_file}")
                    return
                fieldnames = rows[0]

            add_objects_row(rows)
            copy_filename_to_filename2(rows)

            fieldnames.append('filename2')

            # Determine a unique filename2 value to group on; fall back to '' if no entries
            unique_filename2_candidates = [row[-1] for row in rows[1:] if row[-1]]
            unique_filename2 = unique_filename2_candidates[0] if unique_filename2_candidates else ''
            add_rows_above_unique_data(rows, unique_filename2)
            if len(rows) > 1:
                rows[1][0] = unique_filename2

            delete_rows_and_columns(rows)
            delete_first_row(rows)  # Deleting the first row

            with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerows([fieldnames] + rows)

            print(f"Processing complete. Modified data written to '{output_file}'.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def delete_metadata_tmp_file():
        try:
            if os.path.exists("metadataTmp.csv"):
                os.remove("metadataTmp.csv")
                print("Deleted metadataTmp.csv")
        except Exception as e:
            print(f"An error occurred while deleting metadataTmp.csv: {e}")

    input_csv = "metadataTmp.csv"
    output_csv = "metadata1.csv"

    process_csv_second_stage(input_csv, output_csv)

    create_rights_csv()

    delete_metadata_tmp_file()
