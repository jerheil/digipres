"""
Convert metadata1.csv -> metadata.csv

Behavior implemented to match the example metadata-rev.csv:

- Remove the first row whose filename equals exactly "objects" (only the first occurrence).
- For any row whose filename begins with "objects/":
  - Populate dc.title with the text after the last '/' in filename.
  - If dc.format is blank, set it to "1 digital folder".
  - Set dc.description to "Folder contains files relating to {dc.title}".
  - Infer dc.date for the group by inspecting the rows between this group row and the next group row:
    - If one exact date string is common among children, use it.
    - Otherwise extract years from child date strings and return a single year if all the same,
      or "MIN-MAX" if multiple years are present.
- For data rows (typically filenames starting with "data/objects/"):
  - Ensure dc.title is the basename of the filename if empty.
  - Normalize dc.description phrases like "Item is a ppt file relating to ..." to
    "Item is a (ppt) file relating to ..." (wrap file extensions in parentheses if missing).
- After successful conversion, delete metadata1.csv from disk.
"""
import csv
import os
import re
import sys
from collections import Counter

YEAR_RE = re.compile(r'(19\d{2}|20\d{2})')

def basename_from_path(path):
    if not path:
        return ""
    return os.path.basename(path)

def ensure_description_parens(desc):
    """
    Convert "Item is a ppt file relating to X" -> "Item is a (ppt) file relating to X"
    Only applied when the extension is not already in parentheses.
    """
    if not desc:
        return desc
    # only process lines starting with "Item is a " (case-insensitive)
    m = re.match(r'^(Item is a )([A-Za-z0-9]+)( file\b.*)$', desc)
    if m:
        ext = m.group(2)
        tail = m.group(3)
        return f"{m.group(1)}{ext}{tail}"
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
    """
    child_dates: list of date strings (may include full dates like 2008-06-20)
    Return: inferred date:
      - if one exact string appears more than once -> that string
      - else extract years; if none -> first non-empty child date
      - if one unique year -> that year
      - if multiple years -> "min-max"
    """
    vals = [d for d in child_dates if d and d.strip()]
    if not vals:
        return ""

    # frequency of exact strings
    freq = Counter(vals)
    most_common, count = freq.most_common(1)[0]
    if count > 1:
        return most_common

    years = extract_years_from_strings(vals)
    if not years:
        # fallback to first value
        return vals[0]

    min_y = min(years)
    max_y = max(years)
    if min_y == max_y:
        return str(min_y)
    return f"{min_y}-{max_y}"

def convert(infile, outfile):
    # read
    with open(infile, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or ["filename","dc.title","dc.date","dc.format","dc.format2","dc.description"]
        rows = [dict(r) for r in reader]

    # Remove first occurrence where filename == 'objects'
    removed = False
    new_rows = []
    for r in rows:
        fn = (r.get('filename') or "").strip()
        if not removed and fn == 'objects':
            removed = True
            continue
        new_rows.append(r)
    rows = new_rows

    # Find indices of group rows (filename startswith 'objects/')
    group_indices = []
    for idx, r in enumerate(rows):
        fn = (r.get('filename') or "")
        if fn.startswith("objects/"):
            group_indices.append(idx)

    # For each group row, infer date from children and populate fields
    for i, grp_idx in enumerate(group_indices):
        start = grp_idx
        end = group_indices[i+1] if (i+1) < len(group_indices) else len(rows)
        # children are rows start+1 .. end-1
        child_dates = []
        for j in range(start+1, end):
            child = rows[j]
            # skip rows that are themselves group rows (shouldn't be here because end stops there)
            child_dates.append((child.get('dc.date') or "").strip())

        inferred = infer_group_date(child_dates)
        # populate dc.title, dc.format (if blank), dc.description, dc.date (if inferred)
        r = rows[grp_idx]
        fname = (r.get('filename') or "")
        last_seg = fname.rsplit('/', 1)[-1] if fname else ""
        # set title
        r['dc.title'] = last_seg
        # set date if inferred and not empty
        if inferred:
            r['dc.date'] = inferred
        # set format if blank
        if not (r.get('dc.format') and str(r.get('dc.format')).strip()):
            r['dc.format'] = "1 digital folder"
        # set description
        r['dc.description'] = f"Folder contains files relating to {last_seg}"

    # Additional normalization for data rows:
    for r in rows:
        fn = (r.get('filename') or "")
        if fn.startswith("data/objects/"):
            # ensure dc.title is basename
            if not (r.get('dc.title') and r.get('dc.title').strip()):
                r['dc.title'] = basename_from_path(fn)
            # normalize dc.description to put extension in parentheses
            r['dc.description'] = ensure_description_parens(r.get('dc.description') or "")

    # Ensure header ordering matches desired output
    out_fields = ["filename","dc.title","dc.date","dc.format","dc.format2","dc.description"]
    # Add any missing fields at end
    for f in fieldnames:
        if f not in out_fields:
            out_fields.append(f)

    # write
    with open(outfile, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for r in rows:
            # ensure all keys present
            out = {k: (r.get(k) or "") for k in out_fields}
            writer.writerow(out)

def main(argv):
    # Prefer metadata1.csv in current directory if present
    default_input = "metadata1.csv"
    default_output = "metadata.csv"

    if os.path.exists(default_input):
        infile = default_input
        outfile = default_output
    else:
        # Fall back to CLI args:
        if len(argv) >= 3:
            infile = argv[1]
            outfile = argv[2]
        elif len(argv) == 2:
            infile = argv[1]
            outfile = default_output
        else:
            print("No metadata1.csv found and no input file provided.")
            print("Usage:")
            print("  python convert_metadata.py                # will use metadata1.csv -> metadata.csv")
            print("  python convert_metadata.py in.csv out.csv")
            return 2

    if not os.path.exists(infile):
        print(f"Input file not found: {infile}")
        return 1

    convert(infile, outfile)
    print(f"Wrote converted output to {outfile}")

    # Delete metadata1.csv at the end of the script if it exists
    try:
        if os.path.exists("metadata1.csv"):
            os.remove("metadata1.csv")
            print("Deleted metadata1.csv")
    except Exception as e:
        print(f"An error occurred while deleting metadata1.csv: {e}")

if __name__ == "__main__":
    sys.exit(main(sys.argv))