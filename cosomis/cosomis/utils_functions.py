import re, requests

def class_name_to_sentence(class_name: str) -> str:
    words = re.findall(r'[A-Z][a-z]*', class_name)
    if words[-1] == 'View':
        words[-1] = 'Viewed'
    return ' '.join(words)


def get_api_datas(url: str, payload: dict, headers: dict = None) -> list:

    url = f"{url}&page_size=1000" if "?" in url else f"{url}?page_size=1000"

    if not headers:
        headers = {
            "Content-Type": "application/json"
        }

    all_results = []
    links_error = []

    while url:

        response = requests.post(
            url, 
            json=payload, 
            headers=headers
        )
        
        if response.status_code != 200:
            links_error.append(url)
            url = None
        else:
            data = response.json()
            all_results.extend(data["results"])
            url = data["next"]

    return all_results, links_error