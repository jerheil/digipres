import csv
import os
import re
import subprocess
import shutil
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
    exiftool = find_exiftool_executable()
    output_csv = os.path.join(dest_folder, output_name)
    args = [
        exiftool,
        "-csv", "-r",
        "-SourceFile", "-Title", "-FileName", "-FileCreateDate", "-PageCount",
        "-FileTypeExtension", "-MIMEType", "-LayerCount",
        "*"
    ]
    with open(output_csv, "w", encoding="utf-8", newline='') as outfile:
        subprocess.run(args, cwd=source_folder, stdout=outfile, check=True)
    return output_csv

def convert_colons_to_hyphens(date):
    return date.replace(':', '-') if date else ''

def remove_text_from_date(date):
    return date.split()[0] if date else ''

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
    return "data/objects/" + source_file if source_file else ''

def process_layer_count(layer_count, extension, title, filename):
    """
    - If layer_count is numeric: increment and report as Photoshop file with X layers (as before)
    - Otherwise: return "Item is a ({extension}) file relating to {label}"
      where label is Title (if present) else FileName (without its extension).
    """
    layer_count_str = str(layer_count or "")
    extension = extension or ""
    title = title or ""
    filename = filename or ""

    if layer_count_str.isdigit():
        layer_count_num = int(layer_count_str)
        new_layer_count = layer_count_num + 1
        if layer_count_num > 1:
            return f"Item is a Photoshop file with {new_layer_count} layers."
        else:
            return f"Item is a Photoshop file with {new_layer_count} layer."

    label = ""
    if title.strip() and title.strip().upper() != "NULL":
        label = title.strip()
    elif filename.strip():
        base = os.path.basename(filename.strip())
        label = os.path.splitext(base)[0]
    else:
        label = ""

    if extension:
        return f"Item is a extension} file relating to {label}" if label else f"Item is a ({extension}) file."
    else:
        return f"Item is a file relating to {label}" if label else "Item is a file."

def modify_row(row):
    # defensive: if keys missing, ensure defaults to empty strings
    row['FileCreateDate'] = row.get('FileCreateDate', '')
    row['FileCreateDate'] = convert_colons_to_hyphens(row['FileCreateDate'])
    row['FileCreateDate'] = remove_text_from_date(row['FileCreateDate'])
    row['SourceFile'] = add_data_objects_prefix(row.get('SourceFile', ''))
    row['PageCount'] = add_page_count_extension(row.get('PageCount', ''), row.get('FileTypeExtension', ''))
    row['LayerCount'] = process_layer_count(
        row.get('LayerCount', ''),
        row.get('FileTypeExtension', ''),
        row.get('Title', ''),
        row.get('FileName', '')
    )
    return row

def delete_columns(row):
    # Use .pop with default to avoid KeyError
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
            rows = list(reader)

        modified_rows = []

        for row in rows:
            row = modify_row(row)
            row = delete_columns(row)
            row = rename_columns(row)
            modified_rows.append(row)

        with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
            fieldnames_mapping = {
                "filename": "filename",
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

# Second-stage helpers (keeps metadataTmp2 creation)
def add_objects_row(rows):
    if not rows:
        return
    header_len = len(rows[0])
    new_row = ['objects'] + [''] * (header_len - 1)
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
    if len(rows) > 1:
        del rows[1:2]
    for row in rows[1:]:
        if len(row) > 1 and not row[1]:
            row[0] = row[0].replace('data/', '')
    for row in rows:
        if row:
            if len(row) > 0:
                del row[-1]

def delete_first_row(rows):
    if rows:
        del rows[0]

def process_csv_second_stage(input_file, tmp2_output_file):
    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            rows = list(reader)
            if not rows:
                print(f"No rows in {input_file}")
                return
            header = rows[0]

        add_objects_row(rows)
        copy_filename_to_filename2(rows)

        header.append('filename2')

        unique_filename2_candidates = [row[-1] for row in rows[1:] if row[-1]]
        unique_filename2 = unique_filename2_candidates[0] if unique_filename2_candidates else ''
        add_rows_above_unique_data(rows, unique_filename2)
        if len(rows) > 1:
            rows[1][0] = unique_filename2

        delete_rows_and_columns(rows)
        delete_first_row(rows)

        with open(tmp2_output_file, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerows(rows)

        print(f"Intermediate metadata written to '{tmp2_output_file}'.")
    except Exception as e:
        print(f"An error occurred in process_csv_second_stage: {e}")

def create_metadata_from_tmp2(tmp2_file, final_output_file):
    """
    Create metadata1.csv from metadataTmp2.csv.
    """
    try:
        shutil.copyfile(tmp2_file, final_output_file)
        print(f"{final_output_file} created at '{final_output_file}' from '{tmp2_file}'.")
    except Exception as e:
        print(f"An error occurred while creating {final_output_file} from {tmp2_file}: {e}")

def delete_metadata_tmp_file():
    try:
        if os.path.exists("metadataTmp.csv"):
            os.remove("metadataTmp.csv")
            print("Deleted metadataTmp.csv")
    except Exception as e:
        print(f"An error occurred while deleting metadataTmp.csv: {e}")

def delete_metadata_tmp2_file():
    try:
        if os.path.exists("metadataTmp2.csv"):
            os.remove("metadataTmp2.csv")
            print("Deleted metadataTmp2.csv")
    except Exception as e:
        print(f"An error occurred while deleting metadataTmp2.csv: {e}")

# ---------------------------
# Finalization script (convert_metadata.py v3 logic adapted)
# ---------------------------
YEAR_RE = re.compile(r'(19\d{2}|20\d{2})')

def basename_from_path(path):
    if not path:
        return ""
    return os.path.basename(path)

def ensure_description_parens(desc):
    if not desc:
        return desc
    m = re.match(r'^(Item is a )([A-Za-z0-9]+)( file\b.*)$', desc)
    if m:
        ext = m.group(2)
        tail = m.group(3)
        return f"{m.group(1)}({ext}){tail}"
    return desc

def extract_years_from_strings(strings):
    years = []
    for s in strings:
        if not s:
            continue
        for y in YEAR_RE.findall(s):
            try:
                years.append(int(y))
            except Exception:
                pass
    return years

def infer_group_date(child_dates):
    vals = [d for d in child_dates if d and d.strip()]
    if not vals:
        return ""
    freq = Counter(vals)
    most_common, count = freq.most_common(1)[0]
    if count > 1:
        return most_common
    years = extract_years_from_strings(vals)
    if not years:
        return vals[0]
    min_y = min(years)
    max_y = max(years)
    if min_y == max_y:
        return str(min_y)
    return f"{min_y}-{max_y}"

def convert_metadata1_to_metadata(infile="metadata1.csv", outfile="metadata.csv"):
    if not os.path.exists(infile):
        print(f"convert_metadata: input '{infile}' not found, skipping metadata conversion.")
        return

    with open(infile, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or ["filename","dc.title","dc.date","dc.format","dc.format2","dc.description"]
        rows = [dict(r) for r in reader]

    # Find group indices (filename startswith 'objects/')
    group_indices = []
    for idx, r in enumerate(rows):
        fn = (r.get('filename') or "")
        if fn.startswith("objects/"):
            group_indices.append(idx)

    # For each group, infer date from children and populate fields
    for i, grp_idx in enumerate(group_indices):
        start = grp_idx
        end = group_indices[i+1] if (i+1) < len(group_indices) else len(rows)
        child_dates = []
        for j in range(start+1, end):
            child = rows[j]
            child_dates.append((child.get('dc.date') or "").strip())
        inferred = infer_group_date(child_dates)
        r = rows[grp_idx]
        fname = (r.get('filename') or "")
        last_seg = fname.rsplit('/', 1)[-1] if fname else ""
        r['dc.title'] = last_seg
        if inferred:
            r['dc.date'] = inferred
        if not (r.get('dc.format') and str(r.get('dc.format')).strip()):
            r['dc.format'] = "1 digital folder"
        r['dc.description'] = f"Folder contains files relating to {last_seg}"

    # Normalize data rows
    for r in rows:
        fn = (r.get('filename') or "")
        if fn.startswith("data/objects/"):
            if not (r.get('dc.title') and r.get('dc.title').strip()):
                r['dc.title'] = basename_from_path(fn)
            r['dc.description'] = ensure_description_parens(r.get('dc.description') or "")

    out_fields = ["filename","dc.title","dc.date","dc.format","dc.format2","dc.description"]
    for f in fieldnames:
        if f not in out_fields:
            out_fields.append(f)

    with open(outfile, 'w', newline='', encoding='utf-8') as out:
        writer = csv.DictWriter(out, fieldnames=out_fields)
        writer.writeheader()
        for r in rows:
            out_row = {k: r.get(k, "") for k in out_fields}
            writer.writerow(out_row)

    print(f"Converted '{infile}' -> '{outfile}' (metadata post-processing complete).")

# ---------------------------
# Main execution flow
# ---------------------------
def main():
    print("Do you want to generate metadataExp.csv by running exiftool on a folder of files? (y/n)")
    answer = input().strip().lower()
    if answer == "y":
        print("Please select the folder that contains the files to scan with exiftool.")
        source_folder = select_folder_dialog("Select source folder for exiftool")
        if not source_folder:
            print("No source folder selected. Exiting.")
            return
        print("Please select the destination folder where metadataExp.csv should be created.")
        dest_folder = select_folder_dialog("Select destination folder for metadataExp.csv")
        if not dest_folder:
            print("No destination folder selected. Exiting.")
            return
        try:
            generated = run_exiftool_and_create_metadataexp(dest_folder, source_folder, output_name="metadataExp.csv")
            print(f"metadataExp.csv generated at: {generated}")
            input_csv = os.path.join(dest_folder, "metadataExp.csv")
        except FileNotFoundError as fnf:
            print(fnf)
            print("Cannot proceed without exiftool. Exiting.")
            return
        except subprocess.CalledProcessError as cpe:
            print(f"exiftool failed: {cpe}")
            return
    else:
        input_csv = "metadataExp.csv"
        if not os.path.exists(input_csv):
            print(f"'{input_csv}' not found. You can generate it by answering 'y' when prompted next time.")
            return

    tmp_csv = "metadataTmp.csv"
    tmp2_csv = "metadataTmp2.csv"
    metadata1_csv = "metadata1.csv"   # final output from convert.py pipeline
    final_metadata_csv = "metadata.csv"  # output after merged convert_metadata step

    # Stage 1: process metadataExp.csv -> metadataTmp.csv
    add_missing_columns(input_csv)
    process_csv(input_csv, tmp_csv)

    # Stage 2: produce metadataTmp2.csv (intermediate)
    process_csv_second_stage(tmp_csv, tmp2_csv)

    # Stage 3: write metadata1.csv from metadataTmp2.csv
    try:
        shutil.copyfile(tmp2_csv, metadata1_csv)
        print(f"Copied intermediate '{tmp2_csv}' -> '{metadata1_csv}' (convert.py final artifact).")
    except Exception as e:
        print(f"Could not create '{metadata1_csv}' from '{tmp2_csv}': {e}")
        return

    # Stage 4: run merged convert_metadata logic to read metadata1.csv and create metadata.csv
    convert_metadata1_to_metadata(infile=metadata1_csv, outfile=final_metadata_csv)

    # Create rights.csv based on metadataTmp.csv as before
    create_rights_csv()

    # Cleanup metadataTmp.csv and metadataTmp2.csv (keep metadata1.csv for inspection)
    try:
        if os.path.exists("metadataTmp.csv"):
            os.remove("metadataTmp.csv")
            print("Deleted metadataTmp.csv")
    except Exception as e:
        print(f"An error occurred while deleting metadataTmp.csv: {e}")

    try:
        if os.path.exists(tmp2_csv):
            os.remove(tmp2_csv)
            print(f"Deleted {tmp2_csv}")
    except Exception as e:
        print(f"An error occurred while deleting {tmp2_csv}: {e}")

if __name__ == "__main__":
    main()
