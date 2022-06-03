import os
import random
import requests
from bs4 import BeautifulSoup
from collections import Counter
import re
import genanki
import csv
import time
import pickle


def analyse(analyse_text: str, counter):
    characters = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
                  "u",
                  "v", "w", "x", "y", "z", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O",
                  "P",
                  "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z", "+", ".", "1", "2", "3", "4", "5", "6", "7", "8",
                  "9", "0"]
    special = '|'.join(map(re.escape, ("%2C+", "%21+", "%3B+", ".+", "%3F+", "+%2C", "%2C", "%21", "3B", ".", "%3F")))

    # Format the String for the Request
    analyse_text = analyse_text.replace("\n", "+")
    analyse_text = analyse_text.replace(" ", "+")
    for i in analyse_text:
        if not i.isascii():
            continue
        if i not in characters:
            analyse_text = analyse_text.replace(i, f"%{format(ord(i), 'x').upper()}")

    analyse_array = re.split(special, analyse_text)
    analyse_array = [x for x in analyse_array if x]

    # Analyse the Text
    latin_words = []
    request_count = counter
    rounds = 0

    for array in analyse_array:
        url = f"https://www.latin-is-simple.com/de/analysis/?text={array}&sent_seps=.&sent_seps=%2C&sent_seps=%3B" \
              f"&sent_seps=%3F&sent_seps=%21 "
        request = requests.get(url)
        site = BeautifulSoup(request.content, features="html.parser")
        analysis_results = site.find(id="analysis-result")
        try:
            result_request = requests.get(
                f"https://www.latin-is-simple.com/de/analysis/loadsentence?text_id={analysis_results['data-text-id']}&example=false&_={request_count}")
        except Exception:
            continue
        result_site = BeautifulSoup(result_request.content, features="html.parser")
        words = result_site.find_all("div", "word")
        request_count += 1

        for i in words:
            if "no-matches" in i["class"]:
                continue

            match = i.find_all("div", "match")[0]
            a = match.find_all("a")[0]
            word_type = a.find_all("span", "badge")[0].text

            if word_type == "Verb":
                word_cache = re.sub(r" [A-Z]+,", ",", a["title"])
                word_cache = word_cache.replace(" (Dep.)", "")
                word_cache = word_cache.split(", ")
                if len(word_cache) == 4:
                    word = ', '.join([word_cache[2], word_cache[0], word_cache[3]]).lower()
                elif len(word_cache) >= 3 and word_cache[4] == "-":
                    word = ', '.join([word_cache[2], word_cache[0], word_cache[3]]).lower()
                elif len(word_cache) >= 3:
                    word = ', '.join([word_cache[2], word_cache[0], word_cache[3], word_cache[4]]).lower()
                else:
                    word = word_cache[0].lower()
            elif word_type == "Adjektiv":
                word_cache = re.sub(r" [A-Z]+", "", a["title"])
                word_cache = word_cache.rstrip(",")
                word = word_cache.replace("/", ", ")
            elif word_type == "Nomen":
                word_cache = re.sub(r" [A-Z]+", "", a["title"])
                word_cache = word_cache.replace("[", "")
                word = word_cache.replace("]", "")
            else:
                word_cache = re.sub(r" [A-Z]+", "", a["title"])
                word_cache = word_cache.replace(", -", "")
                word = word_cache

            latin_words.append(word)

    request_count += 1000

    if rounds % 20 == 0:
        time.sleep(0.3)

    rounds += 1

    return latin_words, request_count


def translate(counter: Counter):
    latin_words = []
    translations = []
    request_count = 0

    for latin_word, word_count in counter.most_common():
        print(latin_word)
        word_cache = latin_word
        latin_word = latin_word.split(",")

        # Analyse the Site
        url = f"https://www.navigium.de/latein-woerterbuch/{latin_word[0]}?wb=gross&nr=1"
        request = requests.get(url)
        site = BeautifulSoup(request.content, features="html.parser")
        divs = site.find_all("div", "bedeutung")

        if not divs:
            continue

        latin_words.append((word_cache, word_count))
        translation = ','.join(divs[0].text.split(",")[:3])
        translation = re.sub("[\(\[].*?[\)\]]", "", translation)
        translations.append(translation.strip())

        if request_count % 30 == 0:
            time.sleep(0.3)

    print("finsh")
    return latin_words, translations


def analyse_file(filename):
    with open("settings.txt", "r") as f:
        request_count = int(f.read())

    buffer_size = 2000
    latin_words = []
    character_time = 0.032029103085193744

    with open(filename, "r", encoding='utf-8') as file:
        lines = file.readlines(buffer_size)
        file_size = os.stat(f"D:/Development/Languages/Python/AnkiVoc/{filename}").st_size
        remaining_size = file_size
        print("File size:", file_size)
        print("Estimated Time: " + str(round(file_size * character_time + 5, 2)) + "s")
        print("-------------------------")

        while lines:
            start_time = time.time()
            line_size = len(''.join(lines))
            remaining_size -= line_size
            remaining_size -= len(lines)

            latin_words_temp, request_count_temp = analyse("".join(lines), request_count)
            request_count = request_count_temp
            latin_words.extend(latin_words_temp)

            time_period = (time.time() - start_time) / line_size
            character_time = (character_time + time_period) / 2

            print("Progress:", int(100 - round(remaining_size / file_size, 2) * 100), "%")
            if int(round(remaining_size, 0)) + 1 != 0:
                print("Time Left: " + str(round(remaining_size * character_time + 5, 2)) + "s")

            lines = file.readlines(buffer_size)

    with open("settings.txt", "w") as f:
        f.write(str(request_count))

    counter = Counter(latin_words)

    return latin_words, counter


def write_to_text_file(latin_words: list, translations: list, counter: Counter, filename: str, file_title: str,
                       minimum=1):
    with open(filename, "w") as file:
        file.write(file_title + "\n")
        for card in counter.most_common():
            card_text, card_count = card
            if card_count < minimum:
                break
            translation = translations[latin_words.index(card_text)]
            file.write(card_text + " - " + translation + " - " + str(card_count) + "\n")


def write_to_csv_file(latin_words: list, translations: list, counter: Counter, filename: str, minimum=1):
    with open(filename, "wt", newline='') as csv_file:
        field_names = ['latin', 'german']
        writer = csv.DictWriter(csv_file, fieldnames=field_names)

        writer.writeheader()
        for card in counter.most_common():
            card_text, card_count = card
            if card_count < minimum:
                break

            translation = translations[latin_words.index(card_text)]
            writer.writerow({'latin': card_text, 'german': translation})


def write_to_anki_package(latin_words: list, translations: list, filename: str, decks: list, card_name="Karte 1"):
    latin_model = genanki.Model(
        1392434537,
        'Latin_Model',
        fields=[
            {'name': 'Question'},
            {'name': 'Answer'}
        ],
        templates=[
            {
                'name': card_name,
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Answer}} '
            }
        ],
        css='''.card {
             font-family: arial;
             font-size: 20px;
             text-align: center;
             color: black;
             background-color: white;
        }'''
    )

    deck_list = []
    randoms = []
    maximum = 0

    decks_cache: list = decks
    decks_cache.sort(key=lambda x: x[1])
    decks_cache.reverse()

    index_counter = 0

    # minimal included
    # maximal not included
    # maximal = minimal
    for deck in decks_cache:
        deck_name, minimum_card_count = deck

        random_id = random.randint(1 << 30, 1 << 31)
        if random_id in randoms:
            random_id = random.randint(1 << 30, 1 << 31)

        randoms.append(random_id)
        new_deck = genanki.Deck(
            random_id,
            deck_name
        )

        for card_index in range(index_counter, len(latin_words)):
            card_text, card_count = latin_words[card_index]

            if card_count < minimum_card_count:
                index_counter = card_index + 1
                break

            card_text.replace(", -", "")
            translation = translations[card_index]

            if card_text.isdigit():
                continue

            note = genanki.Note(
                model=latin_model,
                fields=[card_text, translation]
            )

            new_deck.add_note(note)

        deck_list.append(new_deck)

    genanki.Package(deck_or_decks=deck_list).write_to_file(filename)


def write_to_binary_file(latin_words: list, counter: Counter, filename: str):
    with open(filename, 'wb') as f:
        data = (latin_words, counter)
        pickle.dump(data, f)
        f.close()


def write_translation_to_binary_file(latin_words: list, german_words: list, filename: str):
    with open(filename, 'wb') as f:
        data = (latin_words, german_words)
        pickle.dump(data, f)
        f.close()


def get_text_from_file(filename: str):
    with open(filename, "r") as file:
        text = file.read()

    return text


def get_data_from_binary_file(filename: str):
    with open(filename, "rb") as file:
        data = pickle.load(file)
    return data


latin, german = get_data_from_binary_file("cicero_translation_binary.txt")
print(latin[:50])
print(german[:50])

# write_to_anki_package(latin, german, "cicero_seneca.apkg", [("A", 15), ("B", 10), ("C", 7), ("D", 5), ("E", 4), ("F", 2)])
