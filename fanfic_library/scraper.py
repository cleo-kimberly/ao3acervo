import requests
from bs4 import BeautifulSoup

def scrape_ao3(url):
    """
    Extrai dados de uma fanfic do AO3 a partir de uma URL.

    Retorna:
        Um dicionário com os dados da fanfic ou None em caso de erro.
    """
    try:
        # O cookie 'view_adult' é importante para bypassar o aviso de conteúdo adulto
        headers = {'User-Agent': 'Mozilla/5.0'}
        cookies = {'view_adult': 'true'}
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # --- Extração de Metadados ---
        title = soup.find('h2', class_='title').get_text(strip=True)
        author = soup.find('a', rel='author').get_text(strip=True)

        # Fandoms
        fandoms_tags = soup.select('dd.fandom.tags a')
        fandoms = ', '.join([tag.get_text(strip=True) for tag in fandoms_tags])

        # Relacionamento (apenas o primeiro "Nome/Nome")
        relationship_tags = soup.select('dd.relationship.tags a')
        relationship = 'N/A'
        for tag in relationship_tags:
            if '/' in tag.get_text(strip=True):
                relationship = tag.get_text(strip=True)
                break
        
        # Tags
        freeform_tags = soup.select('dd.freeform.tags a')
        tags = ', '.join([tag.get_text(strip=True) for tag in freeform_tags])

        # Sumário
        summary_div = soup.select_one('.summary .userstuff')
        summary = summary_div.get_text('\n', strip=True) if summary_div else "Sem sumário."
        
        # Data de Publicação e Status
        stats_dl = soup.find('dl', class_='stats')
        published_dt = stats_dl.find('dt', string='Published:')
        published_dd = published_dt.find_next_sibling('dd') if published_dt else None
        date_published = published_dd.get_text(strip=True) if published_dd else 'N/A'
        
        status_dt = stats_dl.find('dt', string='Status:')
        if not status_dt: # Para one-shots, o status é "Completed"
             status_dt = stats_dl.find('dt', string='Completed:')
        status_dd = status_dt.find_next_sibling('dd') if status_dt else None
        status = status_dd.get_text(strip=True) if status_dd else 'Completed'


        # --- Extração do Conteúdo da Fanfic ---
        content_div = soup.select_one('#chapters .userstuff')
        # Removemos o sumário do início do conteúdo, se presente
        if content_div.find('blockquote', class_='userstuff'):
            content_div.find('blockquote', class_='userstuff').decompose()
            
        content_html = str(content_div)

        return {
            'title': title,
            'author': author,
            'fandom': fandoms,
            'relationship': relationship,
            'summary': summary,
            'tags': tags,
            'status': status,
            'date_published': date_published,
            'content': content_html,
            'source_url': url
        }

    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a URL: {e}")
        return None
    except Exception as e:
        print(f"Erro ao fazer o parsing da página: {e}")
        return None