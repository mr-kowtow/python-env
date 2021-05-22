import requests
from requests import exceptions
import dotenv
import os
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime
import re
import json


base_url = 'https://au.indeed.com/jobs?q=burger&l=Australia&sort=date'
job_url = 'https://au.indeed.com/viewjob?jk='

urllib3.disable_warnings()
dotenv.load_dotenv()
proxy_list = os.getenv('proxy_keys').split(',')

def fetch_html(url):
    while True:
        try:
            proxy = {"https": f'http://scraperapi:{proxy_list[0]}@proxy-server.scraperapi.com:8001'}
            print(url)
            page = requests.get(url, verify=False, proxies=proxy, timeout=60)
            print(page.status_code)
            if page.status_code == 403:
                print('Maximum scraperAPI limit reached, switching keys')
                proxy_list.pop(0)
                continue
            elif page.status_code == 429:
                print('Maximum concurrency limit reached')
                sys.exit()
            page.raise_for_status()  # Raise exceptions if there are request problems
            html = BeautifulSoup(page.content, 'html.parser')
            return html
        except IndexError:
            print('All proxies exhausted.')
            sys.exit()
        except requests.exceptions.HTTPError:
            print(page.status_code)
            print('Skipping')
            continue


def get_job_links(num_jobs):
        """
        Method used to generate the individual job links
        Replaceable if js rendering is available.

        :param num_jobs: number of job links to be returned
        :return: _job_links(list)
        """
        job_list = set()
        query = ''
        pages, remaining_jobs = divmod(num_jobs, 15)

        for page in range(pages + 1):
            try:
                results = fetch_html(base_url + query).find(id='resultsCol')
                print('Request for job list success..')
                jobs = results.findAll(class_='jobsearch-SerpJobCard unifiedRow row result')
                temp = remaining_jobs if page == pages else 15
                for job in jobs[:temp]:
                    job_id = job.attrs['data-jk']
                    link = job_url + job_id
                    job_list.append(link)
                query = f'&start={page * 10}'  # page 2 on indeed is &start=10
            except exceptions.HTTPError:
                print('HTTP error, skipping job')
                continue
            except exceptions.ConnectionError:
                print('Connection Error, skipping job')
                continue
            except exceptions.Timeout:
                print('Requests timed out, try re-checking your links.')
                continue

        return list(job_list)


def get_job_links_today():
    """
    Grabs all job links that are posted today
    Same as job_links method except it scrapes until there are no more jobs for today.

    :return: job links in a list
    """
    job_list = list()
    query = ''
    posted_today = True
    page = 0
    while posted_today:
        try:
            results = fetch_html(base_url + query).find(id='resultsCol')
            jobs = results.findAll(class_='jobsearch-SerpJobCard unifiedRow row result')
            for job in jobs:
                try:
                    date = job.find('span', class_='date').text
                except AttributeError:
                    continue

                if date in ['Just posted', 'Today']:  # No numbers, i.e. today or just now posted.
                    job_id = job.attrs['data-jk']
                    link = job_url + job_id
                    job_list.append(link)
                else:
                    print('No more jobs posted today')
                    posted_today = False
                    return job_list

            page += 1
            query = f'&start={page * 10}'  # page 2 on indeed is &start=10
        except exceptions.HTTPError:
            print('HTTP error, skipping job')
            continue
        except exceptions.ConnectionError:
            print('Connection Error, skipping job')
            continue
        except exceptions.Timeout:
            print('Requests timed out, try re-checking your links.')
            continue


def categorise_position(positions):
    """
    Loops through list of position types and cleans word into specific categories.

    :param positions: List of positions
    :return: List of positions that's been cleaned
    """
    kws = {'full': 'fullTime', 'part': 'partTime', 'intern': 'internship', 'permanent': 'permanent',
           'casual': 'casual', 'sub': 'subContract', 'contract': 'contract', 'temp': 'temporary', 'fly': 'flyInOut'}
    for kw in kws:
        for index, word in enumerate(positions):
            if kw in word.lower():
                positions[index] = kws[kw]
                continue
    return positions


def html_parser(link):
        html = fetch_html(link)
        print('Request success... scraping job.')
        print(link)
        job_container = html.find('div', class_='jobsearch-JobComponent')

        # Get job offer id from the link
        if link:
            pattern = 'jk=.*'
            job_offer_id = re.search(pattern, link).group()[3:]
        else:
            job_offer_id = None

        # Get job offer title
        try:
            job_title = job_container.find('h1', class_='jobsearch-JobInfoHeader-title').text
        except AttributeError:
            job_title = None

        # Get company name
        try:
            company = job_container.find('div', class_='icl-u-lg-mr--sm icl-u-xs-mr--xs').text
        except AttributeError:
            company = None

        # Get company location
        try:
            locations = job_container.find('div', class_='icl-u-xs-mt--xs icl-u-textColor--secondary jobsearch-JobInfoHeader-subtitle '
                                                         'jobsearch-DesktopStickyContainer-subtitle').select('div')[-1].text
            states = ['VIC', 'NSW', 'SA', 'QLD', 'TAS', 'WA', 'ACT', 'NT']

            location = locations.split()
            postcode = None
            state = None
            suburb = ''
            for i in location:
                if re.search(r'\d', i):
                    postcode = i
                elif i in states:
                    state = i
                else:
                    suburb += i + ' '
            suburb = suburb.strip()

        except AttributeError:
            suburb = None
            state = None
            postcode = None

        except IndexError:
            suburb = None
            state = None
            postcode = None

        # Grabbing salary and position_status
        try:
            sal_and_pos = job_container.find('div', class_='jobsearch-JobMetadataHeader-item').findAll('span')
            # If there are two elements , grab both.
            if len(sal_and_pos) == 2:
                salary = sal_and_pos[0].text
                position_status = sal_and_pos[1].text.replace(u'\xa0', '')
                # Hyphen only exists when there are two elements.
                pattern = '-.*?'
                position_status = re.sub(pattern, '', position_status, count=1).replace(' ', '').split(',')
            # Otherwise, if the single element contains digits, assign to salary.
            elif bool(re.search(r'\d', sal_and_pos[0].text)):
                salary = sal_and_pos[0].text
                position_status = []
            # If no digits, assign to position status instead.
            else:
                salary = None

                position_status = sal_and_pos[0].text.replace(u'\xa0', '').replace(' ', '').split(',')
        # When salary & position doesn't exist
        except AttributeError:
            salary = None
            position_status = []

        if position_status:
            position_status = categorise_position(position_status)

        # Get company logo src
        try:
            logo_container = html.find('img', class_='jobsearch-CompanyAvatar-image')
            company_logo = logo_container['src']
            logo_alt = logo_container['alt']
            logo = {'src': company_logo, 'alt': logo_alt}

        # Company doesn't have logo uploaded
        except TypeError:
            logo = None

        # Grab date posted epoch
        try:
            date_posted = job_container.find('div', class_='jobsearch-JobMetadataFooter').text
            temp = re.findall(r'\d+', date_posted)  # Check if number exists
            # If number doesn't exist, job is posted today.
            date_posted = datetime.today().timestamp() if not temp else \
                (datetime.today() - timedelta(days=int(temp[0]))).timestamp()
            date_posted = round(date_posted)
        except AttributeError:
            date_posted = None

        # Grab job description
        try:
            job_description = job_container.find('div', id='jobDescriptionText').text
        except AttributeError:
            job_description = None

        # job_offer = self._job_output_format(job_title, job_offer_id, company, position_status, salary, date_posted,
        #                                     job_description, suburb, state, link, self.reference, l_src=)

        job_offer = {
            'title': job_title,
            'id': job_offer_id,
            'externalId': None,
            'workingVisa': None,
            'visaSubclass': None,
            'company': {
                'name': company,
                'id': '1',  # Our end unique company id
                'logo': logo,
            },
            'positions': position_status,
            'salary': salary,
            'datePosted': date_posted,
            'dateExpiring': None,
            'description': job_description,
            'location': {
                'suburb': suburb,
                'state': state,
                'postcode': postcode,
                'description': None
            },
            'link': link,
            'reference': 'indeed',
            'activeStatus': True,
            'categories': []
        }

        return job_offer


def job_visa_filter(filename):
    """
    Loads json object given in a specific format and filters the job by its description.

    Keywords used:
        kw_visa -> Positively connotated words for working visa.
        temp_visa -> Neutral keywords that mention working/temporary visa.
    filtered_jobs: Jobs are stored in a nested dictionary, separated in a list.

    :return:
    """

    with open(f"data/output/{filename}", 'r') as rf:
        data = json.load(rf)


    kw_visa = ['valid temporary visa', 'valid work permit', '482 ', 'valid visa', 'appropriate visa',
               'current visa', 'temporary visa holder may only occur if no suitable', 'working holiday visa accepted',
               'visa sponsorship support']

    temp_visa = ['temporary visa', 'work visa', 'working visa', 'australian visa']


    for job in data:
        if any(word in job['description'].lower() for word in kw_visa):
            job['workingVisa'] = True
        elif any(word in job['description'].lower() for word in temp_visa):
            job['workingVisa'] = None
        else:
            job['workingVisa'] = False
    
    fpath = f"data/output/filtered_{filename}.json"
    with open(fpath, 'w') as wf:
        json.dump(data, wf)


def main():
    job_links_data = [] 
    jobs_links = get_job_links_today()

    fname = f"job_data_{datetime.today().strftime('%Y_%m_%d')}"
    fpath = f"data/output/{fname}.json"

    for link in jobs_links:
        job_links_data.append(html_parser(link))

    print('Writing jobs to job_data..')
    with open(fpath, "w") as write_file:
        json.dump(job_links_data, write_file)

    print('Writing filtered jobs to filteredJobs..')
    job_visa_filter(fname)

if __name__ == '__main__':
    main()