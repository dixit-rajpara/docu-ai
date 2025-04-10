import html2text
from bs4 import BeautifulSoup


def html_to_markdown(html: str) -> str:
    converter = html2text.HTML2Text()
    converter.ignore_links = True
    converter.ignore_images = True
    converter.body_width = 0
    return converter.handle(html).strip()


def clean_html_soup(soup: BeautifulSoup):
    # Remove tags but keep their content
    for tag in soup.find_all(["a"]):
        tag.unwrap()

    # Remove whole tags and their content
    for tag_name in [
        "script",
        "style",
        "noscript",
        "iframe",
        "canvas",
        "svg",
        "object",
        "embed",
        "form",
        "input",
        "button",
        "nav",
        "footer",
        "header",
        "aside",
        "video",
        "audio",
    ]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove empty lists
    for list_tag in soup.find_all(["ul", "ol"]):
        li_items = list_tag.find_all("li")
        has_non_empty_item = any(li.get_text(strip=True) for li in li_items)
        if not li_items or not has_non_empty_item:
            list_tag.decompose()

    for img in soup.find_all("img"):
        alt_text = img.get("alt")
        if alt_text:
            img.replace_with(alt_text)
        else:
            img.decompose()


def html_to_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def html_to_clean_markdown(html: str) -> str:
    soup = html_to_soup(html)
    clean_html_soup(soup)
    return html_to_markdown(str(soup))
