import ankiconnect
import requests
from bs4 import BeautifulSoup
import argparse
import copy

forvo_api = "1fea57783d85698bc845cdb9749cc4ac"
DEFAULT_NOTE = {
    "deckName": "Russian Vocabulary",
    "modelName": "Russian Word",
    "fields": {
        "Word": "",
        "Read": "",
        "Meaning": "",
        "Pos": "",
        "Genitive Suffix": "",
        "Sentence": "",
        "Sentence-Translation": "",
        "Notes": "",
        "Audio": "",
    },
    "options": {
        "closeAfterAdding": False,
        "allowDuplicate": False,
        "duplicateScope": "deck",
        "duplicateScopeOptions": {
            "deckName": "Default",
            "checkChildren": False,
            "checkAllModels": False
        }
    },
}

def getNoteJson(input_word, note):
    url = "https://dict.com/russian-english/{}".format(input_word)
    page = requests.get(url)
    if (page.status_code != 200):
        print("request failed", url)
        return

    soup = BeautifulSoup(page.content, 'html.parser')
    card = soup.find("div", class_="mcard mcardnone")
    if "no entry" in card.get_text():
        print("Not in dict:", input_word)
        return

    try:
        word = card.find('input', {'id': 'IdxWrd'}).get('value')
        reading = card.find('span', 'lex_ful_entr l1').get_text() + card.find('span', 'lex_ful_pron').get_text()[1:]
        pos_html = card.find('span', 'lex_ful_morf')
        pos = pos_html.get_text() if pos_html else ""
        form_html = card.find('span', 'lex_ful_form')
        form = form_html.get_text()[1:-1] if form_html else ""
        meaning = "; ".join([m.get_text() for m in card.find_all('span', 'lex_ful_tran w l2')])
        
    except Exception as e:
        print("Exception %s" % str(e))
        return

    note["fields"]["Word"] = word
    note["fields"]["Read"] = reading
    note["fields"]["Meaning"] = meaning
    note["fields"]["Pos"] = pos 
    note["fields"]["Genitive Suffi"] = form
    return note

def getForvoPronun(input_word, note):
    if not note["fields"]["Word"]:
        note["fields"]["Word"] = input_word
    word = note["fields"]["Word"]
    url = "https://apifree.forvo.com/action/word-pronunciations/format/json/word/{}/id_lang_speak/138/order/rate-desc/key/{}/".format(word, forvo_api)
    response = requests.get(url)
    if (response.status_code != 200):
        print("Forvo request failed for word", word, url)
        return
    data = response.json()
    items = data["items"][:5]
    if not len(items):
        print("No audio for word", word)
        return
    for idx, item in enumerate(items):
        mp3_link = item["pathmp3"]
        print(mp3_link)
        if idx == 0:
            note["audio"] = [{
                "url": mp3_link,
                "filename": "forvo_qiwen_{}.mp3".format(word),
                "fields": [
                    "Audio"
                ]
            }]
    return note


parser = argparse.ArgumentParser(description='Input to Anki Russian Vocab')
parser.add_argument('words', type=str, nargs='+')
parser.add_argument('--no-dict', action='store_true', help='do not pull definition, only pull audio')
args = parser.parse_args()

for word in args.words:
    note = copy.deepcopy(DEFAULT_NOTE)
    if not args.no_dict:
        note = getNoteJson(word, note)
    if note:
        note = getForvoPronun(word, note)
        result = ankiconnect.invoke('guiAddCards', note=note)

