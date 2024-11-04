import json
import sys
import re

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
    UniqueItemPattern = re.compile(r"^Item_.*?_Unique")
    
    for key, eng_value in eng_data.items():
        '''
        if key.startswith("Affix_legendary_"):
            jp_value = jp_data.get(key, {}).get("Name", "")
            eng_name = eng_value.get("Name", "")

            # そのまま出力版
            jp_name = jp_value
            eng_name = eng_name
            result.append({eng_name: jp_name})

            # "化身"をつけて出力版
            if eng_name.startswith("of"):
                eng_name = "Aspect " + eng_name
            else:
                eng_name = eng_name + " Aspect"
            jp_name = jp_value + "化身"
            result.append({eng_name: jp_name})
        ''' 
            
        ''' 
        if key.startswith("ParagonNode_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        ''' 


        '''
        if key.startswith("ParagonGlyph_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        '''


        '''
        if key.startswith("Affix_Damage_Tag_"):
            eng_prefix = eng_value.get("Name_Prefix", "")
            jp_prefix = jp_data.get(key, {}).get("Name_Prefix", "")
            eng_suffix = eng_value.get("Name_Suffix", "")
            jp_suffix = jp_data.get(key, {}).get("Name_Suffix", "")
            result.append({eng_prefix + " Aspect": jp_prefix + "化身"})
            result.append({"Aspect " + eng_suffix: jp_suffix + "化身"})
        if key == "NecromancerArmy.stl":
            for sub_key, eng_sub_value in eng_value.items():
                jp_sub_value = jp_data.get(key, {}).get(sub_key, "")
                result.append({eng_sub_value: jp_sub_value})
        if key.startswith("Recipe_Tempering_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        '''

        '''
        # UniqueItemとのマッチング
        if UniqueItemPattern.match(key):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        '''
        
        '''
        # S5化身とのマッチング1
        if key.startswith("Affix_S05_BSK_"):
            jp_value = jp_data.get(key, {}).get("Name", "")
            eng_name = eng_value.get("Name", "")

            # そのまま出力版
            jp_name = jp_value
            eng_name = eng_name
            result.append({eng_name: jp_name})

            # "化身"をつけて出力版
            if eng_name.startswith("of"):
                eng_name = "Aspect " + eng_name
            else:
                eng_name = eng_name + " Aspect"
            jp_name = jp_value + "化身"
            result.append({eng_name: jp_name})

        # S5化身とのマッチング2 必要かも
        '''

        '''
        # S6化身とのマッチング1
        if key.startswith("Affix_x1_legendary_"):
            jp_value = jp_data.get(key, {}).get("Name", "")
            eng_name = eng_value.get("Name", "")

            # そのまま出力版
            jp_name = jp_value
            eng_name = eng_name
            result.append({eng_name: jp_name})

            # "化身"をつけて出力版
            if eng_name.startswith("of"):
                eng_name = "Aspect " + eng_name
            else:
                eng_name = eng_name + " Aspect"
            jp_name = jp_value + "化身"
            result.append({eng_name: jp_name})
        '''

        '''
        # ルーン名のマッチング
        if key.startswith("Item_Rune_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        '''
            

        '''
        if key.startswith("Item_"):
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        '''

        '''
        if key.startswith("Power_"):
            eng_name = eng_value.get("name", "")
            jp_name = jp_data.get(key, {}).get("name", "")
            result.append({eng_name: jp_name})
        '''
        

        '''
        # Item_*****_Legendary_Generic_
        pattern = re.compile(r'^Item_.*?_Legendary_Generic_')
        if pattern.match(key):
            print(key)
            eng_name = eng_value.get("Name", "")
            jp_name = jp_data.get(key, {}).get("Name", "")
            result.append({eng_name: jp_name})
        '''
        
        # 第1キーが"AttributeDescriptions.stl"の場合に処理を行う
        if key == "AttributeDescriptions.stl":
            for sub_key, eng_sub_value in eng_value.items():
                # 英語のvalueに対する加工処理
                processed_eng_value = clean_attribute_description(eng_sub_value)
                
                # 日本語のvalueを取得し、加工処理
                jp_sub_value = jp_data.get(key, {}).get(sub_key, "")
                processed_jp_value = clean_attribute_description(jp_sub_value)
                
                # 結果を追加
                result.append({processed_eng_value: processed_jp_value})
        
    return result

def clean_attribute_description(value):
    value = re.sub(r'\{c_label\}(.*?)\{/c\}', '\\1', value)
    # [ ]で囲まれた部分を除去
    value = re.sub(r'\[.*?\]', '', value)
    # {c_important}と{/c}と{value}を除去
    value = re.sub(r'\{c_important\}', '', value)
    value = re.sub(r'\{/c\}', '', value)
    value = re.sub(r'\{/c\}', '', value)
    value = re.sub(r'\{VALUE\d\}', '', value)
    value = re.sub(r'\{VALUE%\}', '', value)
    value = re.sub(r'\{c:[0-9A-Fa-f]{6,8}\}', '', value)
    value = re.sub(r'\{/c:[0-9A-Fa-f]{6,8}\}', '', value)
    
    # 記号を除去
    value = re.sub(r'[+{}|]', '', value)
    # トリム
    return value.strip()


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
