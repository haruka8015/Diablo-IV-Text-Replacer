import json
import sys

def load_json(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_json(data, filename):
    with open(filename, 'w', encoding='utf-8') as file:
        file.write('{\n')
        for i, entry in enumerate(data):
            key = list(entry.keys())[0]
            value = entry[key]
            escaped_key = key.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
            escaped_value = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
            file.write(f'    "{escaped_key}": "{escaped_value}"')
            if i < len(data) - 1:
                file.write(',\n')
        file.write('\n}')

def transform_data(eng_data, jp_data):
    result = []
    
    for key, eng_value in eng_data.items():
        '''
        if key.startswith("Affix_legendary_"):
            jp_value = jp_data.get(key, {}).get("Name", "")
            eng_name = eng_value.get("Name", "")
            if eng_name.startswith("of"):
                eng_name = "Aspect " + eng_name
            else:
                eng_name = eng_name + " Aspect"
            jp_name = jp_value + "化身"
            result.append({eng_name: jp_name})
        elif key.startswith("ParagonNode_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        
        elif key.startswith("ParagonGlyph_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        
        elif key.startswith("Affix_Damage_Tag_"):
            eng_prefix = eng_value.get("Name_Prefix", "")
            jp_prefix = jp_data.get(key, {}).get("Name_Prefix", "")
            eng_suffix = eng_value.get("Name_Suffix", "")
            jp_suffix = jp_data.get(key, {}).get("Name_Suffix", "")
            result.append({eng_prefix + " Aspect": jp_prefix + "化身"})
            result.append({"Aspect " + eng_suffix: jp_suffix + "化身"})
        
        elif key == "NecromancerArmy.stl":
            for sub_key, eng_sub_value in eng_value.items():
                jp_sub_value = jp_data.get(key, {}).get(sub_key, "")
                result.append({eng_sub_value: jp_sub_value})
        
        elif key.startswith("Recipe_Tempering_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        '''
#        elif key.startswith("Item_"):
#            eng_name = eng_value.get("Name", "")
#            jp_name = jp_data.get(key, {}).get("Name", "")
#            result.append({eng_name: jp_name})
#       
#        el
        if key.startswith("Power_"):
            eng_name = eng_value.get("name", "")
            jp_name = jp_data.get(key, {}).get("name", "")
            result.append({eng_name: jp_name})
    
    return result

def main():
    if len(sys.argv) != 4:
        print("Usage: python script.py <english_json> <japanese_json> <output_json>")
        return

    eng_filename = sys.argv[1]
    jp_filename = sys.argv[2]
    output_filename = sys.argv[3]

    eng_data = load_json(eng_filename)
    jp_data = load_json(jp_filename)

    transformed_data = transform_data(eng_data, jp_data)
    
    save_json(transformed_data, output_filename)

if __name__ == "__main__":
    main()
