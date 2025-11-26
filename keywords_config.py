# keywords_config.py
# lists to boost detection and synonyms for expansion

TECH_SKILLS = [
    "python","java","c++","c","c#","javascript","typescript","sql","nosql",
    "html","css","react","angular","vue","node","django","flask","spring",
    "aws","azure","gcp","docker","kubernetes","git","linux","bash",
    "tensorflow","pytorch","keras","machine learning","deep learning",
    "data science","nlp","computer vision","opencv","pandas","numpy",
    "matplotlib","scikit-learn","rest api","api","mongodb","mysql","postgresql"
]

ROLE_KEYWORDS = [
    "software engineer","software developer","backend developer","frontend developer",
    "fullstack","devops","data scientist","machine learning engineer",
    "ml engineer","ai engineer","research intern","intern"
]

# mapping common variants to canonical
SYNONYMS = {
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "js": "javascript",
    "py": "python",
    "mlear": "machine learning"
}
