import datetime
import re
import scrapy

def parse_date(s):
    m = re.match('(\\d+)年(\\d+)月(\\d+)日', s)
    if m:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None

def parse_kaiji(s):
    m = re.match('第(\\d+)回', s)
    if m:
        return int(m.group(1))
    return None

def parse_nichiji(s):
    m = re.match('第(\\d+)日', s)
    if m:
        return int(m.group(1))
    return None

def parse_time(s):
    m = re.match('(\\d+):(\\d+\\.\\d)', s)
    if m:
        return int(m.group(1))*60 + float(m.group(2))
    m = re.match('(\\d+\\.\\d)', s)
    if m:
        return float(m.group(1))
    return None

def parse_odds(s):
    m = re.match('(\\d+\\.\\d)', s)
    if m:
        return float(m.group(1))
    return None


class RakutenKeibaSpider(scrapy.Spider):
    name = 'rakuten_keiba'
    allowed_domains = ['keiba.rakuten.co.jp']
    start_urls = ['https://keiba.rakuten.co.jp/race_performance/list/']

    def parse(self, response):  # Day
        for url in response.css('a::attr("href")').re('https://keiba.rakuten.co.jp/race_performance/list/RACEID/[0-9]{8}0000000000'):
            yield scrapy.Request(
                response.urljoin(url),
                callback=self.parse,
                priority=-3,
            )
        for url in response.css('a::attr("href")').re('https://keiba.rakuten.co.jp/race_performance/list/RACEID/[0-9]{18}'):
            if url[-10:] == '0000000000':
                continue
            yield scrapy.Request(
                response.urljoin(url),
                callback=self.parse_day_racecourse,
                priority=-1,
            )

    def parse_day_racecourse(self, response):  # Day / Racecourse
        for url in response.css('a::attr("href")').re('https://keiba.rakuten.co.jp/race_card/list/RACEID/[0-9]{18}'):
            if url[-10:] == '0000000000':
                continue
            if url[-2:] == '00':
                continue
            yield scrapy.Request(
                response.urljoin(url),
                callback=self.parse_day_racecourse_race_card,
                priority=-2,
            )

    def parse_day_racecourse_race_card(self, response):  # Day / Racecourse / Race / Card
        race = {
            'slots': []
        }

        race['日付'] = parse_date(response.css('.raceNote .trackState li::text').extract()[0].strip())
        if datetime.date.today() <= race['日付']:
            return
        race['回次'] = parse_kaiji(response.css('.raceNote .trackState li::text').extract()[1].strip())
        race['競馬場'] = response.css('.raceNote .trackState li::text').extract()[2].strip()
        race['日次'] = parse_nichiji(response.css('.raceNote .trackState li::text').extract()[3].strip())

        race['距離'] = response.css('.raceNote .trackState .distance::text').extract()[0].strip()
        for (dt, dd) in zip(response.css('.raceNote .trackState li dl dt::text').extract(), response.css('.raceNote .trackState li dl dd::text').extract()):
            if dt == '天候：':
                race['天候'] = dd
            elif dt == 'ダ：':
                race['ダ'] = dd
            elif dt == '芝：':
                race['芝'] = dd
            elif dt == '発走時刻':
                race['発走時刻'] = dd
            else:
                raise Exception()

        for tr in response.css('table tbody tr'):
            if len(tr.css('tr::attr("class")').extract()) != 1:
                continue
            slot = {}
            for th in tr.css('th'):
                class_list = th.css('th::attr("class")').extract()
                if len(class_list) != 1:
                    continue
                class_ = class_list[0]
                if class_ == 'position':
                    slot['枠番'] = int(''.join(th.css('th::text').extract()).strip())

            for td in tr.css('td'):
                class_list = td.css('td::attr("class")').extract()
                if len(class_list) != 1:
                    continue
                class_ = class_list[0]

                if class_ == 'number':
                    number = ''.join(td.css('td::text').extract()).strip()
                    if number == '':  # 取消 or 除外
                        slot['馬番'] = None
                    else:
                        slot['馬番'] = int(number)

                if class_ == 'name':
                    slot['父馬'] = ''.join(td.css('.name::text').extract()).split('\n')[1].strip()
                    slot['馬名'] = ''.join(td.css('.mainHorse a::text').extract()).strip()
                    slot['母馬'] = ''.join(td.css('.name::text').extract()).split('\n')[4].strip()
                    slot['母父馬'] = ''.join(td.css('.append::text').extract()).split('\n')[2].strip()

                    odds = (''.join(td.css('.append .rate::text').extract())).strip()
                    slot['オッズ'] = parse_odds(odds)
                    if slot['オッズ'] is None:
                        odds = (''.join(td.css('.append .rate .hot::text, .append .rate .dark::text').extract())).strip()
                        slot['オッズ'] = parse_odds(odds)

                    slot['誕生日'] = ''.join(td.css('.append::text').extract()).split('\n')[4].strip()
                    slot['馬主名'] = ''.join(td.css('.append::text').extract()).split('\n')[5].strip()
                    slot['生産牧場'] = ''.join(td.css('.append::text').extract()).split('\n')[6].strip()

                if class_ == 'profile':
                    slot['性齢'] = ''.join(td.css('.profile::text').extract()).split('\n')[1].strip()
                    slot['毛色'] = ''.join(td.css('.profile::text').extract()).split('\n')[2].strip()
                    slot['負担重量'] = float(''.join(td.css('.profile::text').extract()).split('\n')[3].strip())
                    slot['騎手名'] = ''.join(td.css('.profile::text').extract()).split('\n')[6].strip()
                    slot['勝率'] = float(td.css('.hot::text, .dark::text').extract()[0].strip()[:-1]) * 0.01
                    slot['3着内率'] = float(td.css('.hot::text, .dark::text').extract()[1].strip()[:-1]) * 0.01
                    slot['調教師名'] = ''.join(td.css('.profile::text').extract()).split('\n')[9].strip()

                if class_ == 'weight':
                    slot['連対時馬体重1'] = ''.join(td.css('.weight::text').extract()).split('\n')[0].strip()
                    slot['連対時馬体重2'] = ''.join(td.css('.weight::text').extract()).split('\n')[2].strip()

                if class_ == 'weightDistance':
                    slot['馬体重増減1'] = ''.join(td.css('.weightDistance::text').extract()).split('\n')[0].strip()
                    slot['馬体重増減2'] = ''.join(td.css('.weightDistance::text').extract()).split('\n')[2].strip()

            race['slots'].append(slot)

        url = response.url.replace('race_card', 'race_performance')
        return scrapy.Request(
            response.urljoin(url),
            callback=self.parse_day_racecourse_race_performance,
            meta={
                'race': race,
            },
        )

    def parse_day_racecourse_race_performance(self, response):
        race = response.meta['race']
        for tr in response.css('table tbody tr'):
            position = None
            for th in tr.css('th'):
                class_list = th.css('th::attr("class")').extract()
                if len(class_list) != 1:
                    continue
                class_ = class_list[0]

                if class_ == 'position':
                    position = int(''.join(th.css('th::text').extract()).strip())
            if position is None:
                continue

            for td in tr.css('td'):
                class_list = td.css('td::attr("class")').extract()
                if len(class_list) != 1:
                    continue
                class_ = class_list[0]

                if class_ == 'order':
                    order = ''.join(td.css('td::text').extract()).strip()
                    if order == '-':  # 取消 or 除外
                        race['slots'][position-1]['着順'] = None
                    else:
                        race['slots'][position-1]['着順'] = int(order)

                if class_ == 'weightTax':
                    race['slots'][position-1]['負担重量'] = float(''.join(td.css('td::text').extract()).strip())

                if class_ == 'jockey':
                    race['slots'][position-1]['騎手'] = ''.join(td.css('td::text').extract()).strip()

                if class_ == 'time':
                    race['slots'][position-1]['タイム'] = parse_time(''.join(td.css('td::text').extract()).strip())

                if class_ == 'lead':
                    race['slots'][position-1]['着差'] = ''.join(td.css('td::text').extract()).strip()

                if class_ == 'spurt':
                    race['slots'][position-1]['推定上がり'] = ''.join(td.css('td::text').extract()).strip()

                if class_ == 'rank':
                    race['slots'][position-1]['人気'] = ''.join(td.css('td::text').extract()).strip()

#        print(race)
        return race
