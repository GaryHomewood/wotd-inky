import jinja2
import requests, os, sys
from bs4 import BeautifulSoup
import json
from html2image import Html2Image
from PIL import Image
import sys

# Platform detection to allow for dev before deploy
RASPBERRY_PI = os.uname()[4][:3] == 'arm'
if RASPBERRY_PI:
  from inky import InkyWHAT

# Get a JSON representation of the word of the day with a scraper
def get_wotd_json():
    URL = 'https://www.dictionary.com/e/word-of-the-day/'

    try:
        html = requests.get(URL).text
        document = BeautifulSoup(html, 'html.parser')
        word_wrapper = document.find_all('div', class_='otd-item-wrapper-content')
        resp = {}
        word_idx = 1
        for i, el in enumerate(word_wrapper):
            # Word
            word = el.find('div', class_='wotd-item').find('div', class_='otd-item-headword__word')
            resp[word_idx] = {}
            resp[word_idx]['word'] = word.find('h1').text

            # Pronunciation
            pronunciation_text = el.find('span', class_='otd-item-headword__pronunciation__text')
            pronunciation = ''
            for child in pronunciation_text.children:
                if child.text.strip() != '':
                    if (child.name == 'span'):
                        # Replace spans with semantic html equivalent
                        classes = (child.attrs['class'])
                        has_bold = [s for s in classes if "bold" in s]
                        if (has_bold):
                            child.name = "em"
                            del child['class']
                        has_italic = [s for s in classes if "italic" in s]
                        if (has_italic):
                            child.name = "i"
                            del child['class']
                        # tag as string
                        pronunciation += str(child)
                    else:
                        pronunciation += child.string.strip().replace(" ", "")

            resp[word_idx]['pronunciation'] = pronunciation

            # Word type and definition
            word_definition_wrapper = el.find('div', class_='otd-item-headword__pos')
            word_definition = list(word_definition_wrapper.children)
            resp[word_idx]['type'] = word_definition[1].text.strip()
            resp[word_idx]['definition'] = word_definition[3].text.strip()

            word_idx += 1

        word_idx = 1

        # About and examples of usage
        for i, el in enumerate(word_wrapper):
            el2  = el.find('div', class_='wotd-item-origin')
            ul = el2.find_all('ul')
            resp[word_idx]['about'] = str(ul[0]).replace('\n', '')
            resp[word_idx]['examples'] = str(ul[1]).replace('\n', '')
            word_idx += 1

        json_resp = json.dumps(resp, indent=4)
        return json_resp
    except requests.exceptions.ConnectionError:
        print("You've got problems with connection.", file=sys.stderr)
        return None

# Draw to the eInk display
def inky_show(img_png):
  if RASPBERRY_PI:
    inky_display = InkyWHAT('red')
    # Image must be converted to an RGB palette to display
    img_pal = Image.new('P', (1,1))
    img_pal.putpalette((255, 255, 255, 0, 0, 0, 255, 0, 0) + (0, 0, 0) * 252)
    img_eink = img_png.convert('RGB').quantize(palette=img_pal)
    
    # Rotate the image because the power suppl is at the top.
    inky_display.set_image(img_eink.rotate(180))
    inky_display.set_border(inky_display.BLACK)
    inky_display.show()

def main():
    wotd_json = get_wotd_json()
    if (wotd_json == None):
        sys.exit()
    data = json.loads(wotd_json)

    # Use a template to convert the json to a minimal semantic webpage (with styling)
    cwd = os.path.dirname(os.path.abspath(__file__))
    loader = jinja2.FileSystemLoader(os.path.join(cwd, 'templates'))
    env = jinja2.Environment(loader=loader)
    template = env.get_template('wotd.html')
    html = template.render(data=data)

    # Save webpage to file
    page = open((os.path.join(cwd, 'wotd.html')), 'w')
    page.write(html)
    page.close()

    # Save html as an image
    image_path = os.path.join(cwd, 'wotd.png')
    hti = Html2Image(
        custom_flags=['--disable-gpu'],
        output_path = cwd
    )
    hti.screenshot(
        html_str=html,
        size=(400, 300),
        save_as='wotd.png'
    )

    # Display the image on the eInk
    img_png = Image.open(image_path).resize((400, 300))
    inky_show(img_png)

main()
