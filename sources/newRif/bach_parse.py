import re
import json
from rif_utils import path, tags_map
from data_utilities.util import getGematria
from tags_fix_and_check import tags_by_criteria, save_tags, next_gem, pages_range, page_tags
from tags_compare import compare_tags_nums, compare_tags, OrderedCounter
from sg_parser import check_sequence

def parse_bach_pars(data, masechet):
    letter_tag = tags_map[masechet]['bach_letter']
    data = [letter_tag + par for par in data.split(letter_tag)][1:]
    return data

def parse_regular_masechet(data, masechet, tags, unknowns):
    data = data.strip()
    if data == '': return [], {}, []
    letter_tag = tags_map[masechet]['bach_letter']
    lengths = []
    newdata = []
    data = parse_bach_pars(data, masechet)
    splitted = []
    cou = 0
    for par in data:
        if letter_tag + '(א' in par and '&' not in par:
            if cou:
                lengths.append(cou)
                splitted.append(page_text)
            cou = 1
            page_text = []
        else:
            cou += 1
        page_text.append(par)
    lengths.append(cou)
    splitted.append(page_text)
    newtags, counter = compare_tags_nums(tags, lengths, unknowns, 3)
    tags.update(newtags)
    save_tags(tags, masechet)
    if len(counter) > 0:
        newdata = [[] for _ in range(max([int(page) for page in counter]) + 1)]
        for page in counter:
            newdata[int(page)] = splitted.pop(0)
    return newdata, tags, lengths

def execute():
    with open(f'{path}/bach_exceptions.txt', encoding='utf-8') as fp:
        exceptions = fp.read()
    exceptions = exceptions.split('@')
    for masechet in tags_map:
        if not tags_map[masechet]['bach_letter']: continue
        print(masechet)
        with open(path+'/commentaries/bach_{}.txt'.format(masechet), encoding='utf-8') as fp:
            data = fp.read()
        excep = [e for e in exceptions if masechet in e]
        if excep: excep = excep[0]
        data = re.sub('\ufeff|\u200f', '', data)
        page_tag = tags_map[masechet]['bach_page']
        letter_tag = tags_map[masechet]['bach_letter']
        tags = tags_by_criteria(masechet, value=lambda x: x['referred text']==3)
        unknowns = tags_by_criteria(masechet, value=lambda x: x['referred text']==0 and x['style']==1)
        lengths = []
        newdata = []

        if page_tag:
            data = data.split('@88')[1:]
            for page in data:
                try:
                    daf, amud = re.search('^דף ([א-פ][א-ט]?) ע"([אב])', page).groups()
                    daf_num = getGematria(daf)
                    if amud == 'א': amud = 1
                    elif amud == 'ב': amud = 2
                    else: print('amud isnt valid', page[:30])
                    section = daf_num * 2 - 3 + amud
                    while len(newdata) < section: newdata.append([])
                    page = re.sub('דף [א-ס][א-ט]? ע"[אב]', f'@88{daf}{"." if amud==1 else ":"}', page).strip()
                except (ValueError, AttributeError):
                    print('daf and amud arent valid', page[:30])
                page = parse_bach_pars(page, masechet)
                newdata.append(page)

            lengths = [len(page) for page in newdata if page != []]

        else:
            newdata = [[] for _ in pages_range(tags)]
            for _ in range(12): newdata.append([]) #if the maechet has notes but the data has no tags in the last pages
            dones = [0]
            unplaced_data = []
            for placed in re.findall(r'@11[^1]*@%\d{1,3}@%', data):
              comment, page, _ = placed.split('@%')
              page = int(page)
              newdata[page-1].append(parse_bach_pars(comment, masechet)[0]) #all comments in page should be marked
              dones.append(page)
              new_part, data = data.split(placed, 1)
              unplaced_data.append(new_part)
            unplaced_data.append(data)
            for n, page in enumerate(dones[:-1]):
              next_p = dones[n+1]-1
              part_data = unplaced_data[n]
              part_tags = tags_by_criteria(tags, key=lambda x: page<=int(x[1:4])<next_p)
              part_unk = tags_by_criteria(unknowns, key=lambda x: page<=int(x[1:4])<next_p)
              part_data, part_tags, part_leng = parse_regular_masechet(part_data, masechet, part_tags, part_unk)
              newdata[page: len(part_data)] = part_data[page:]
              tags.update(part_tags)
              lengths += part_leng
            page = dones[-1]
            part_data = unplaced_data[-1]
            part_tags = tags_by_criteria(tags, key=lambda x: page<=int(x[1:4]))
            part_unk = tags_by_criteria(unknowns, key=lambda x: page<=int(x[1:4]))
            part_data, part_tags, part_leng = parse_regular_masechet(part_data, masechet, part_tags, part_unk)
            newdata[page:] = part_data[page:]
            tags.update(part_tags)
            lengths += part_leng

        tags.update(compare_tags(tags, lengths, unknowns, 3, exceptions=excep))
        check_sequence(newdata, letter_tag+r'\(')
        save_tags(tags, masechet)

        newdata = [[re.sub(' +', ' ', par).strip() for par in page] for page in newdata]
        with open(path+'/commentaries/json/bach_{}.json'.format(masechet), 'w') as fp:
            json.dump(newdata, fp)

if __name__ == '__main__':
    execute()
