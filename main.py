from bs4 import BeautifulSoup

import requests
import time
import json
import re


class CityRestaurants:
    def __init__(self, url, city):
        self.url = url
        self.city = city
        self.total_restaurants = 0
        self.localities = []
        self.localities_url = []
        self.data = []
        self.headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0'}

    # Get all localities from the given city
    def get_localities(self):
        r = self.make_request(self.url)
        if not r:
            return
        soup = BeautifulSoup(r.content, 'html.parser')
        l = soup.find('div', {'class': 'ui segment row'})
        links = l.find_all('a')
        for link in links:
            self.total_restaurants += self.get_number(link.find('span').text)
            self.localities_url.append(link['href'])
            self.localities.append(link['title'][15:])

    # All restaurants from given city
    def get_all_restaurant_links(self):
        for link, name in zip(self.localities_url, self.localities):
            self.data.append({
                'url': self.get_restaurant_links(link),
                'locality': name
                })

    # For any particular locality
    def get_restaurant_links(self, url):
        next_page = True
        temp_links = []
        url = url + '?all=1&nearby=0'
        while next_page:
            r = self.make_request(url)
            if not r:
                return temp_links
            soup = BeautifulSoup(r.content, 'html.parser')
            l = soup.find_all('a', {'class': 'result-title'})
            links = [i['href'] for i in l]
            temp_links += links
            next_pagination = soup.find_all('a', {'class': 'next'})
            if next_pagination:
                next_pagination = next_pagination[-1]
            else:
                break
            next_page = True if next_pagination['aria-label'] == 'Next Page' else False
            url = 'https://www.zomato.com' + next_pagination['href']
        return temp_links

    def get_all_restaurant_details(self):
        for data in self.data:
            temp_data = []
            for url in data['url']:
                temp_data.append(self.get_restaurant_details(url))
            data['restaurants'] = temp_data

    def get_restaurant_details(self, url):
        r = self.make_request(url)
        if not r:
            return {}
        soup = BeautifulSoup(r.content, 'html.parser')
        title = soup.find('a', {'class': 'large'})
        popular_food = soup.find('div', {'class': 'rv_highlights__section pr10'})
        rating = soup.find('div', {'class': 'rating-div'})
        features = soup.find('div', {'class': 'res-info-highlights'})
        timings = soup.find('div', {'class': 'res-week-timetable'})
        collections = soup.find_all('span', {'class': 'res-page-collection-text'})
        address = soup.find('div', {'class': 'res-main-address'})
        phone_number = soup.find('span', {'class': 'tel'})
        if rating and (rating['aria-label'].strip() != 'NEW' and rating['aria-label'].strip() != '-'):
            rating = float(rating['aria-label'].strip())
            rating_count = int(soup.find('span', {'itemprop': 'ratingCount'}).text)
            rating_percentage = [self.get_number(j.text) for i in soup.find_all('div', {'class': 'progress_con'}) for j in i.find_all('div', {'class': 'ml6'})]
        else:
            rating = None
            rating_count = None
            rating_percentage = []

        cusinies = soup.find('div', {'class': 'res-info-cuisines'})
        info = soup.find('span', {'class': 'res-info-estabs'})
        average_cost = soup.find('div', {'class': 'res-info-detail'})
        if average_cost:
            average_cost = average_cost.find('span', {'tabindex': 0})
        return {
                'title': title.text.strip() if title else None,
                'rating': rating,
                'info': info.text.strip().split(',') if info else None,
                'rating_count': rating_count,
                'rating_percentage': rating_percentage,
                'phone_number': [i.text.strip() for i in phone_number.find_all('span', {'class': 'tel'})] if phone_number else [],
                'timings': [i.text for i in timings.find_all('td', {'class': 'pl10'})] if timings else [],
                'features': [i.text.strip() for i in features.find_all('div', recursive=False)] if features else [],
                'cuisines': [i.text for i in cusinies.find_all('a')] if cusinies else [],
                'address': address.text.strip() if address else None,
                'average_cost': average_cost.text.strip() if average_cost else None,
                'popular_food': popular_food.find('div', {'class':'ln18'}).text.strip().replace('  ', '').replace('\n', '') if popular_food else [],
                'collections': [i.text.strip() for i in collections] if collections else []
                }

    def generate_json(self):
        return {
                'total_restaurants': self.total_restaurants,
                'localities': self.localities,
                'data': self.data,
                }

    def make_request(self, url):
        print(url)
        r = requests.get(url, headers=self.headers)
        print('Details', r.status_code)
        count = 0
        if r.status_code == 200:
            return r
        else:
            while r.status_code != 200:
                r = requests.get(url, headers=self.headers)
                print('New details', r.status_code)
                if r.status_code == 200:
                    return r
                else:
                    count += 1
                    time.sleep(count*2)
                    if count == 5:
                        return None


    # Get number from a given string
    def get_number(self, x):
        return int(re.search(r'\d+', x).group())


if __name__ == '__main__':
    main_data = {}
    r = requests.get('https://www.zomato.com/india', headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:58.0) Gecko/20100101 Firefox/58.0'})
    soup = BeautifulSoup(r.content, 'html.parser')
    links = soup.find('div', {'class': 'mtop'}).find_all('a')
    main_data['total_city'] = len(links)
    main_data['data'] = {}
    class_city = {data['title']: CityRestaurants(url=data['href'], city=data['title']) for data in links}

    for city in class_city.keys():
        print('\n\n\nGetting Localities for', class_city[city].city)
        class_city[city].get_localities()
        print('Getting Restaurant Links')
        class_city[city].get_all_restaurant_links()
        print('Getting  Restaurant Details')
        class_city[city].get_all_restaurant_details()
        json_data = class_city[city].generate_json()
        main_data['data'][class_city[city].city] = json_data

    # We need to save the data so that is not written here
