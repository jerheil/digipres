import csv
import os
from datetime import datetime

def convert_colons_to_hyphens(date):
    return date.replace(':', '-')

def remove_text_from_date(date):
    return date.split()[0]

def add_page_count_extension(page_count, extension):
    if extension in ["psd", "jpg", "tif", "png"]:
        return f"1 photograph ({extension})"
    else:
        return f"{page_count} p. ({extension})"

def add_data_objects_prefix(source_file):
    return "data/objects/" + source_file

def process_layer_count(layer_count):
    if layer_count.isdigit():
        layer_count = int(layer_count)
        new_layer_count = layer_count + 1

        if layer_count > 1:
            return f"Item is a Photoshop file with {new_layer_count} layers."
        else:
            return f"Item is a Photoshop file with {new_layer_count} layer."
    else:
        return f"Item is a ."

def modify_row(row):
    row['FileCreateDate'] = convert_colons_to_hyphens(row['FileCreateDate'])
    row['FileCreateDate'] = remove_text_from_date(row['FileCreateDate'])
    row['SourceFile'] = add_data_objects_prefix(row['SourceFile'])
    row['PageCount'] = add_page_count_extension(row['PageCount'], row.get('FileTypeExtension', ''))
    row['LayerCount'] = process_layer_count(row['LayerCount'])
    return row

def delete_columns(row):
    del row["Title"]
    del row["FileTypeExtension"]
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
    fieldnames = rows[0].keys()
    if "PageCount" not in fieldnames:
        fieldnames = list(fieldnames) + ["PageCount"]
    if "LayerCount" not in fieldnames:
        fieldnames = list(fieldnames) + ["LayerCount"]
    if "Title" not in fieldnames:
        fieldnames = list(fieldnames) + ["Title"]
    return fieldnames, rows

def add_missing_columns(input_file):
    try:
        with open(input_file, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            rows = list(reader)

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
        doc_id_type = input("Enter 'u' for University Records Transfer or 'd' for Deed of Gift: ")
        doc_id_value = input("Enter a document ID value in the format ####-###: ")

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
                    "end_date": f"{int(start_date[:4]) + 100}-" + start_date[5:],
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
    input_csv = "metadataExp.csv"
    output_csv = "metadataTmp.csv"

    # Add missing columns if necessary
    add_missing_columns(input_csv)

    process_csv(input_csv, output_csv)

    # The second set of subroutines
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
        del rows[1:2]  # Delete rows 2 and 3
        for row in rows[1:]:
            if not row[1]:  # If dc.title is blank
                row[0] = row[0].replace('data/', '')  # Delete "data/" from filename
        for row in rows:
            del row[-1]  # Delete filename2 column

    def delete_first_row(rows):
        del rows[0]  # Delete the first row
            
    def process_csv(input_file, output_file):
        try:
            with open(input_file, 'r', newline='', encoding='utf-8') as infile:
                reader = csv.reader(infile)
                rows = list(reader)
                fieldnames = rows[0]

            add_objects_row(rows)
            copy_filename_to_filename2(rows)

            fieldnames.append('filename2')

            unique_filename2 = list(set(row[-1] for row in rows[1:]))[0]
            add_rows_above_unique_data(rows, unique_filename2)
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
            os.remove("metadataTmp.csv")
            print("Deleted metadataTmp.csv")
        except Exception as e:
            print(f"An error occurred while deleting metadataTmp.csv: {e}")
    
    input_csv = "metadataTmp.csv"
    output_csv = "metadata.csv"

    process_csv(input_csv, output_csv)

    create_rights_csv()

    delete_metadata_tmp_file()
