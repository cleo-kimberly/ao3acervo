import requests
from bs4 import BeautifulSoup

def scrape_ao3(url):
    """
    Extrai metadados de uma fanfic do AO3 a partir de uma URL.
    Não baixa mais o conteúdo da história.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        cookies = {'view_adult': 'true'}
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        title = soup.find('h2', class_='title').get_text(strip=True)
        author = soup.find('a', rel='author').get_text(strip=True)
        fandoms_tags = soup.select('dd.fandom.tags a')
        fandoms = ', '.join([tag.get_text(strip=True) for tag in fandoms_tags])

        relationship = 'N/A'
        relationship_tags = soup.select('dd.relationship.tags a')
        for tag in relationship_tags:
            if '/' in tag.get_text(strip=True):
                relationship = tag.get_text(strip=True)
                break
        
        freeform_tags = soup.select('dd.freeform.tags a')
        tags = ', '.join([tag.get_text(strip=True) for tag in freeform_tags])

        summary_div = soup.select_one('.summary .userstuff')
        summary = summary_div.get_text('\n', strip=True) if summary_div else "Sem sumário."
        
        stats_dl = soup.find('dl', class_='stats')
        published_dt = stats_dl.find('dt', string='Published:')
        published_dd = published_dt.find_next_sibling('dd') if published_dt else None
        date_published = published_dd.get_text(strip=True) if published_dd else 'N/A'
        
        status_dt = stats_dl.find('dt', string='Status:')
        if not status_dt:
             status_dt = stats_dl.find('dt', string='Completed:')
        status_dd = status_dt.find_next_sibling('dd') if status_dt else None
        status = status_dd.get_text(strip=True) if status_dd else 'Completed'

        # O conteúdo da fanfic NÃO é mais baixado.
        return {
            'title': title,
            'author': author,
            'fandom': fandoms,
            'relationship': relationship,
            'summary': summary,
            'tags': tags,
            'status': status,
            'date_published': date_published,
            'source_url': url
        }

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a URL: {e}")
        return None
    except Exception as e:
        print(f"Erro ao fazer o parsing da página: {e}")
        return None