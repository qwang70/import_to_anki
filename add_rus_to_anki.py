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
    "audio": []
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

def getForvoPronun(word, note):
    url = "https://apifree.forvo.com/action/word-pronunciations/format/json/word/{}/id_lang_speak/138/order/rate-desc/key/{}/".format(word, forvo_api)
    response = requests.get(url)
    if (response.status_code != 200):
        print("Forvo request failed for word", word, url)
        return
    data = response.json()
    if not len(data["items"]):
        print("No audio for word", word)
        return
    item = data["items"][0]
    mp3_link = item["pathmp3"]
    #print(mp3_link)
    note["audio"].append({
        "url": mp3_link,
        "filename": "forvo_qiwen_{}.mp3".format(word),
        "fields": [
            "Audio"
        ]
    })
    return note

def getForvoPronuns(input_words, note):
    empty_result = True
    if not note["fields"]["Word"]:
        note["fields"]["Word"] = ", ".join(input_words)
    for word in input_words:
        if getForvoPronun(word, note):
            empty_result = False

    if empty_result:
        return
    return note


parser = argparse.ArgumentParser(description='Input to Anki Russian Vocab')
parser.add_argument('words', type=str, nargs='+')
parser.add_argument('--no-dict', action='store_true', help='do not pull definition, only pull audio')
args = parser.parse_args()

note = copy.deepcopy(DEFAULT_NOTE)
if len(args.words) == 1:
    for word in args.words:
        if not args.no_dict:
            note = getNoteJson(word, note)
        if note:
            if not note["fields"]["Word"]:
                note["fields"]["Word"] = word
            note = getForvoPronun(note["fields"]["Word"], note)
            result = ankiconnect.invoke('guiAddCards', note=note)
elif len(args.words) > 1 and args.no_dict:
    note = getForvoPronuns(args.words, note)
    result = ankiconnect.invoke('guiAddCards', note=note)
