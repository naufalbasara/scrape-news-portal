import re, os, pandas as pd, time, requests, logging, json, pytz

from pprint import pprint
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import get_rootdir
from datetime import datetime, timedelta, date
from dateutil.relativedelta import *
from utils.GSheet import GSheet

root_dir = get_rootdir()

def get_driver(headless:bool = True, no_sandbox:bool = True) -> webdriver:
    chrome_options = webdriver.ChromeOptions()
    if headless: chrome_options.add_argument('--headless')
    if no_sandbox: chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('auto-open-devtools-for-tabs')
    chrome_options.page_load_strategy = 'none'

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)

    return driver, wait

def getNavLinks(endpoint:str, driver:webdriver, update:bool) -> list[str]:
    result = {'title': [], 'href': []}
    wait = WebDriverWait(driver, 10)
    driver.get(endpoint)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#main-menu')))
    driver.execute_script("window.stop();")

    page = BeautifulSoup(driver.page_source, 'html.parser')
    try:
        menuTag = getattr(page.find('div', class_='main-menu', id='main-menu'), 'div', None)
        navs = menuTag.findChildren('ul')
        for nav_list in navs:
            for link in nav_list.find_all('li'):
                # add link to the list
                try:
                    result['title'].append(link.a['title'])
                    result['href'].append(link.a['href'])
                except:
                    embedded_list = link.ul
                    for link_2 in embedded_list.find_all('li'):
                        result['title'].append(link_2.a['title'])
                        result['href'].append(link_2.a['href'])
        if update:
            if os.path.exists(os.path.join(root_dir, 'result_data')) == False:
                os.mkdir(os.path.join(root_dir, 'result_data'))
            pd.DataFrame(result).to_excel(os.path.join(root_dir, 'result_data', 'navigation_links.xlsx'))
            print("File saved locally.")
    except Exception as error:
        print(f'Failed to get nav links due to: {error}')
    
    return result

def getNewsArticles(driver:webdriver, url:str, publishLimit:datetime) -> list[str]:
    newsLinks = []
    try:
        driver.get(url)
        sectionSoup = BeautifulSoup(driver.page_source, 'html.parser')
        # sectionSoup.findAll('li', class_='art-list')
        newsList = sectionSoup.find('ul', id='latestul')

        nextArticle = newsList.findNext('li')
        title = nextArticle.find_next('h3').a['title']
        href = nextArticle.find_next('h3').a['href']
        datePublished = nextArticle.find_next('time', class_='timeago')['title']
        datePublished = datetime(*[*map(int, datePublished.split()[0].split('-'))])
        newsLinks.append({'title': title, 'href': href, 'datePublished': datePublished})

        while nextArticle!= None or datePublished >= publishLimit:
            print(f'Fetching data from {href} ({datePublished})')

            href = nextArticle.find_next('h3').a['href']
            title = nextArticle.find_next('h3').a['title']
            datePublished = nextArticle.find_next('time', class_='timeago')['title']
            datePublished = datetime(*[*map(int, datePublished.split()[0].split('-'))])

            newsLinks.append({'title': title, 'href': href, 'datePublished': datePublished})
            print()

            if nextArticle == None:
                try:
                    driver.execute_script('loadmore();')
                    time.sleep(3)
                    nextArticle = nextArticle.findNext('li')
                    if nextArticle == None: break
                except Exception as error:
                    print(f"[ERROR]: Failed in getting article details {error}")
                    break
            
            nextArticle = nextArticle.findNext('li')
    except Exception as error:
        print(f"[ERROR]: {error}")
        pass

    return newsLinks

def getArticles(driver:webdriver, wait, url:str, publishLimit:datetime) -> list[str]:
    newsLinks = []
    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#latestul')))
        driver.execute_script("window.stop();")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        articlesList = soup.find('ul', id='latestul')
        post = articlesList.find_next('li', class_='art-list')

        while soup.find('div', id='ltldmr') == None:
            try:
                post = post.find_next_sibling('li', class_='art-list')
                title = post.find_next('h3')
                print(title.a['title'])
                datePublished = post.find_next('time', class_='timeago')['title']
                datePublished = datetime(*[*map(int, datePublished.split()[0].split('-'))])
                
                newsLinks.append({
                    'title':title.a['title'], 'href':title.a['href'],
                    'publishedDate': datePublished
                    })
                
                if datePublished <= publishLimit:
                    break
            except:
                driver.execute_script("loadmore();")
                soup = BeautifulSoup(driver.page_source, 'html.parser')
            
    except Exception as e:
        print(f'Failed to fetch all the articles from {url}: {e}')

    return newsLinks

def getPageContent(driver:webdriver, wait, url:str) -> dict:
    time.sleep(1)
    content_obj = {}
    content = ''
    print('fetching url')

    # get total page
    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.txt-article')))
        driver.execute_script("window.stop();")
        content_soup = BeautifulSoup(driver.page_source)
        paging_container = getattr(content_soup.find('div', class_='paging'), 'div', None)
        # get title
        content_obj['title'] = getattr(content_soup.find('h1', id='arttitle'), 'text', None)
            
        # get writer and editor
        content_obj['writer'] = getattr(content_soup.find('h5', id='penulis'), 'text', None)
            
        # get main news article content
        container = content_soup.find('div', class_='txt-article')
        for paragraph in container.find_all('p'):
            content += paragraph.text + '\n'

        if paging_container != None:
            totalPage = len(paging_container.findChildren('a'))
            for numberPage in range(2, totalPage+1):
                driver.get(url + f'?page={numberPage}')
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.txt-article')))
                driver.execute_script("window.stop();")
                content_soup = BeautifulSoup(driver.page_source)
                
                # get title
                content_obj['title'] = getattr(content_soup.find('h1', id='arttitle'), 'text', None)
                    
                # get writer and editor
                content_obj['writer'] = getattr(content_soup.find('h5', id='penulis'), 'text', None)
                
                # get main news article content
                container = content_soup.find('div', class_='txt-article')
                for paragraph in container.find_all('p'):
                    content += paragraph.text + '\n'
    except Exception as error:
        print(f'[ERROR]: Failed due to {error}')
        totalPage = 1
        
    content_obj['content'] = content

    return content_obj

if __name__ == "__main__":
    endpoint = 'https://surabaya.tribunnews.com/'
    selected_menu = ['Pemilu', 'Super Ball', 'Travel', 'Otomotif', 'Techno', 'Kesehatan']
    time_filter = True
    months_back = 5

    # initiate driver object
    driver, wait = get_driver(headless=False, no_sandbox=False)
    driver.implicitly_wait(5)

    # # get all navigation links
    # nav_links = getNavLinks(endpoint, driver=driver, update=True)
    # nav_df = pd.read_excel(os.path.join(root_dir, 'result_data/navigation_links.xlsx'))
    # nav_df = nav_df.set_index('title').loc[selected_menu, :]

    # get all the articles link in each of the submenu
    selected_obj = {}
    obj = {
        'Super Ball': {'url': 'https://surabaya.tribunnews.com/ajax/latest_section?',
                       'callback':'jQuery36307699751906099292_1716523270689', 'start':'0','img':'thumb2', 'section':'70877','category':'','section_name':'superball', '_':'1716523270690'},
        'Pemilu': {
            'url':'https://surabaya.tribunnews.com/ajax/latest_section?',
            'callback':'jQuery3630683777923478224_1716523392512', 'start':'0','img':'thumb2', 'section':'70884','category':'','section_name':'pemilu', '_':'1716523392513'},
        'Travel': {
            'url': 'https://surabaya.tribunnews.com/ajax/latest_section?',
            'callback':'jQuery36302362740593506103_1716523421432', 'start':'0','img':'thumb2', 'section':'70826','category':'','section_name':'travel', '_':'1716523421433'},
        'Otomotif': {
            'url': 'https://surabaya.tribunnews.com/ajax/latest_section?',
            'callback':'jQuery363038001083309593753_1716523446362', 'start':'0','img':'thumb2', 'section':'70879','category':'','section_name':'otomotif', '_':'1716523446363'},
        'Techno':{
            'url': 'https://surabaya.tribunnews.com/ajax/latest_section?',
            'callback':'jQuery36309681226112120138_1716523467217', 'start':'0','img':'thumb2', 'section':'70825','category':'','section_name':'techno', '_':'1716523467218'},
        'Kesehatan':{'url':'https://surabaya.tribunnews.com/ajax/latest_section?',
                     'callback':'jQuery36308512665524126286_1716523482026', 'start':'0','img':'thumb2', 'section':'70880','category':'','section_name':'kesehatan', '_':'kesehatan'}
        }
    for menu in selected_menu:
        selected_obj[menu] = obj[menu]
    
    for category in selected_obj.keys():
        if os.path.exists(os.path.join(root_dir, f'result_data/article_links/{category}')) == False:
            os.mkdir(os.path.join(root_dir, f'result_data/article_links/{category}'))

        url = selected_obj[category]['url']
        for _ in range(0, 1020, 20):
            url = f"{url}callback={selected_obj[category]['callback']}&start={_+1 if _!=0 else _}&img={selected_obj[category]['img']}&section={selected_obj[category]['section']}&category={selected_obj[category]['category']}&section_name={selected_obj[category]['section_name']}&_={selected_obj[category]['_']}"
            driver.get(url)
            soup = BeautifulSoup(driver.page_source,'html.parser')
            callback = url[re.search(r'callback=jQuery[0-9]+_[0-9]*&', url).span()[0]:re.search(r'callback=jQuery[0-9]+_[0-9]*&', url).span()[1]-1]
            callback = callback[callback.index('=')+2:]
            content = soup.find('pre').text
            content = content[re.search(callback, content).end()+1:len(content)-1]
            with open(os.path.join(root_dir, f'result_data/article_links/{category}/start-{_+1}.json'), 'w') as json_file:
                json.dump(content, json_file)

    # get all the page content
    menu_list = []
    content_list = []
    writer_list = []
    time_list = []
    for menu in selected_menu:
        print(f"============= GETTING CONTENT FOR MENU {menu} =============")
        for fp in os.listdir(os.path.join(root_dir, 'result_data', 'article_links', menu)):
            try:
                with open(os.path.join(root_dir, 'result_data', 'article_links', menu, fp), 'r') as json_file:
                    posts = json.loads(json.load(json_file))["posts"]
                    print(fp)
                    for post in posts:
                        print(f"============= GETTING CONTENT FOR POST {post['title']} ({datetime.fromisoformat(post['date'])}) =============")
                        if time_filter:
                            if datetime.fromisoformat(post['date']) <= datetime.now().replace(tzinfo=pytz.UTC) - relativedelta(months=months_back):
                                break

                        try:
                            content_result_obj = getPageContent(driver, wait, post['url'])
                            menu_list.append(menu)
                            content_list.append(content_result_obj['content'])
                            writer_list.append(content_result_obj['writer'])
                            time_list.append(post['date'])

                            # checkpoint every 100 data
                            if len(content_list)%100 == 0:
                                print(f'saving to csv {len(content_list)}...')
                                pd.DataFrame({'label':menu_list, 'content': content_list}).to_csv(os.path.join(root_dir, f'result_data/result-{len(content_list)}.csv'))

                        except Exception as error:
                            print(f"============= FAILED AT POST {post['title']}: {error} =============")
                            menu_list.append(None)
                            content_list.append(None)
                            writer_list.append(None)
                            time_list.append(None)
            except Exception as error:
                print(f"============= FAILED TO READ JSON {fp}: {error} =============")


    try:
        print('saving to csv...')
        pd.DataFrame({'label':menu_list, 'content': content_list, 'writer': writer_list, 'time': time_list}).to_csv(os.path.join(root_dir, f'result_data/{date.today().strftime("%d-%B-%Y")}_result.csv'))
    except:
        print('saving to excel...')
        pd.DataFrame({'label':menu_list, 'content': content_list, 'writer': writer_list, 'time': time_list}).to_excel(os.path.join(root_dir, f'result_data/{date.now().strftime("%d-%B-%Y")}_result.csv'))

    driver.close()