import pydicom
import csv
from pydicom.datadict import dictionary_VR, keyword_for_tag

def find_ui_tags_in_csv(csv_path):
    ui_tags = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            group = int(row['group'], 16)
            element = int(row['element'], 16)
            tag = (group << 16) | element
            try:
                vr = dictionary_VR(tag)
                if vr == 'UI':
                    keyword = keyword_for_tag(tag)
                    ui_tags.append((tag, keyword))
            except KeyError:
                pass
    return ui_tags

if __name__ == "__main__":
    ui_tags = find_ui_tags_in_csv('table_e1_1_tags.csv')
    print(f"{'Tag':<12} | {'Keyword':<40}")
    print("-" * 55)
    for tag, keyword in ui_tags:
        print(f"({(tag >> 16):04X}, {(tag & 0xFFFF):04X}) | {keyword}")
