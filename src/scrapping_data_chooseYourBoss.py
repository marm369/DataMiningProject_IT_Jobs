import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import json
import os
import re
from urllib.parse import urljoin, quote

class ChooseYourBossScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/',
        })
        self.base_url = "https://www.chooseyourboss.com"
        
    def make_request(self, url, max_retries=3):
        """Faire une requête avec retry et gestion d'erreur améliorée"""
        for attempt in range(max_retries):
            try:
                # Pause aléatoire plus longue
                time.sleep(random.uniform(3, 7))
                
                response = self.session.get(url, timeout=20)
                print(f"   📊 Status: {response.status_code}")
                
                if response.status_code == 403:
                    print("   🚫 Accès refusé (403). Le site nous bloque.")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10
                        print(f"   ⏳ Attente de {wait_time} secondes avant réessai...")
                        time.sleep(wait_time)
                        continue
                    else:
                        return None
                        
                elif response.status_code == 429:
                    print("   🚦 Trop de requêtes (429). Attente plus longue...")
                    time.sleep(30)
                    continue
                    
                elif response.status_code != 200:
                    print(f"   ❌ Erreur HTTP: {response.status_code}")
                    return None
                    
                return response
                
            except requests.exceptions.Timeout:
                print(f"   ⏱️ Timeout sur l'essai {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                    
            except requests.exceptions.ConnectionError:
                print(f"   🔌 Erreur de connexion sur l'essai {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                    
            except Exception as e:
                print(f"   ❌ Erreur inattendue: {e}")
                if attempt < max_retries - 1:
                    time.sleep(10)
                    continue
                    
        return None
    
    def scrape_search_last_120_days(self, keyword="développeur", max_pages=3):
        """Scraper uniquement les offres des 120 derniers jours"""
        all_offers = []
        cutoff_date = datetime.now() - timedelta(days=120)
        stopped_for_old_offers = False
        
        print(f"📅 COLLECTE DES OFFRES DES 120 DERNIERS JOURS")
        print(f"📅 Date de coupure: {cutoff_date.strftime('%d/%m/%Y')}")
        print("=" * 60)
        
        for page in range(1, max_pages + 1):
            if stopped_for_old_offers:
                break
                
            print(f"\n🔍 Page {page} pour '{keyword}'...")
            
            # CORRECTION : URL dynamique basée sur le mot-clé
            keyword_encoded = quote(keyword.lower().replace(' ', '-'))
            search_url = f"{self.base_url}/offres/emploi-{keyword_encoded}?p={page}"
            
            print(f"   📡 URL: {search_url}")
            
            response = self.make_request(search_url)
            
            if not response:
                print(f"   ❌ Échec de la requête pour la page {page}")
                continue
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier si nous sommes sur une page de blocage
            if "accès refusé" in soup.get_text().lower() or "access denied" in soup.get_text().lower():
                print("   🚫 PAGE DE BLOCAGE DÉTECTÉE")
                break
            
            job_cards = self._find_job_cards_improved(soup)
            
            if not job_cards:
                print(f"   ➤ Aucune offre trouvée pour '{keyword}'")
                break
            
            print(f"   📄 {len(job_cards)} offres trouvées sur cette page")
            
            page_offers = 0
            old_offers_count = 0
            
            for i, card in enumerate(job_cards, 1):
                print(f"    📋 Traitement offre {i}/{len(job_cards)}")
                offer = self._parse_job_card_with_date_check(card, keyword, cutoff_date)
                
                if offer:
                    if offer.get("est_dans_periode", True):
                        all_offers.append(offer)
                        page_offers += 1
                        offer_date = datetime.fromisoformat(offer["date_publication_reelle"])
                        print(f"     ✅ Offre récente ({offer_date.strftime('%d/%m/%Y')})")
                    else:
                        old_offers_count += 1
                        offer_date = datetime.fromisoformat(offer["date_publication_reelle"])
                        print(f"     ❌ Offre trop ancienne ({offer_date.strftime('%d/%m/%Y')})")
                        
                        # Si plusieurs offres anciennes d'affilée, arrêter
                        if old_offers_count >= 3 and i > 3:
                            print("   🛑 Plusieurs offres anciennes détectées - arrêt de la collecte")
                            stopped_for_old_offers = True
                            break
                else:
                    print(f"     ❌ Offre non parsée")
                
                time.sleep(random.uniform(2, 4))
            
            print(f"   📊 Résumé page {page}: {page_offers} offres récentes, {old_offers_count} offres anciennes")
            
            # Si aucune offre récente sur cette page, arrêter
            if page_offers == 0 and not stopped_for_old_offers:
                print("   ⏹️  Aucune offre récente sur cette page - arrêt de la collecte")
                break
            
            if page < max_pages and not stopped_for_old_offers:
                pause_time = random.uniform(5, 10)
                print(f"💤 Pause de {pause_time:.1f} secondes avant la page suivante...")
                time.sleep(pause_time)
        
        return all_offers
    
    def _parse_job_card_with_date_check(self, card, keyword, cutoff_date):
        """Parser une carte d'offre avec vérification de la date"""
        try:
            # Extraire le lien principal
            link_elem = card.find('a', href=True)
            if not link_elem:
                return None
                
            job_url = urljoin(self.base_url, link_elem['href'])
            
            # Titre
            title = link_elem.get_text(strip=True)
            if not title or len(title) < 5:
                title_elem = card.find(['h2', 'h3', 'h4'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            if not title:
                return None
            
            # Extraire la date de publication depuis la carte
            publication_date = self._extract_publication_date_from_card(card)
            
            # Si pas de date trouvée dans la carte, essayer d'extraire de la page détail
            if not publication_date:
                print(f"     📅 Extraction date depuis page détail...")
                publication_date = self._extract_publication_date_from_detail(job_url)
            
            # Si toujours pas de date, utiliser la date actuelle (cas par défaut)
            if not publication_date:
                publication_date = datetime.now()
                print(f"     ⚠️  Date non trouvée, utilisation date actuelle")
            else:
                print(f"     📅 Date extraite: {publication_date.strftime('%d/%m/%Y')}")
            
            # Vérifier si l'offre est dans la période des 120 jours
            est_dans_periode = publication_date >= cutoff_date
            
            # Entreprise
            company = "Non spécifié"
            parent_text = card.get_text()
            company_patterns = [
                r'chez\s+([A-Za-z0-9&\.\-\' ]+)',
                r'at\s+([A-Za-z0-9&\.\-\' ]+)',
            ]
            
            for pattern in company_patterns:
                match = re.search(pattern, parent_text, re.IGNORECASE)
                if match:
                    company = match.group(1).strip()
                    break
            
            # Localisation
            location = "Non spécifié"
            location_patterns = [
                r'à\s+([A-Za-z0-9\- ]+)',
                r'in\s+([A-Za-z0-9\- ]+)',
                r'\(([A-Za-z0-9\- ]+)\)'
            ]
            
            for pattern in location_patterns:
                match = re.search(pattern, parent_text, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    break
            
            # Créer l'offre de base
            offer = {
                "intitule_poste": title,
                "nom_entreprise": company,
                "ville_region": location,
                "date_publication": datetime.now().isoformat(),  # Date de collecte
                "date_publication_reelle": publication_date.isoformat(),  # Date réelle de l'offre
                "type_contrat": "CDI",
                "experience_demandee": "",
                "niveau_seniorite": "Non spécifié",
                "description_poste": "",
                "source_offre": job_url,
                "teletravail": "Non",
                "competences_mentionnees": [],
                "fourchette_salaire": "",
                "metier_recherche": keyword,
                "id_offre": job_url.split('/')[-1] or str(hash(job_url)),
                "date_collecte": datetime.now().isoformat(),
                "est_dans_periode": est_dans_periode,
                "jours_ecoules": (datetime.now() - publication_date).days
            }
            
            # Si l'offre est dans la période, récupérer les détails
            if est_dans_periode:
                print(f"     📖 Extraction des détails pour: {title[:30]}...")
                detail_offer = self._scrape_job_detail_improved(job_url, keyword)
                if detail_offer:
                    offer.update(detail_offer)
            
            return offer
                
        except Exception as e:
            print(f"❌ Erreur parsing carte: {e}")
            return None
    
    def _extract_publication_date_from_card(self, card):
        """Extraire la date de publication depuis la carte"""
        try:
            # Chercher des éléments de date communs
            date_selectors = [
                'time',
                '.date',
                '.publication-date',
                '.job-date',
                '.offer-date',
                'span[class*="date"]',
                'div[class*="date"]',
                '.timestamp',
                '.time-ago'
            ]
            
            for selector in date_selectors:
                date_elem = card.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    parsed_date = self._parse_date_text(date_text)
                    if parsed_date:
                        return parsed_date
            
            # Chercher dans le texte de la carte par motifs
            card_text = card.get_text()
            date_patterns = [
                r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',  # DD/MM/YYYY
                r'(\d{1,2}\s+\w+\s+\d{4})',  # 15 janvier 2024
                r'il y a (\d+) jour',  # il y a 3 jours
                r'il y a (\d+) heure',  # il y a 2 heures
                r'(\w+) dernier',  # hier
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, card_text, re.IGNORECASE)
                if matches:
                    parsed_date = self._parse_date_text(matches[0])
                    if parsed_date:
                        return parsed_date
            
            return None
            
        except Exception as e:
            print(f"     ❌ Erreur extraction date carte: {e}")
            return None
    
    def _extract_publication_date_from_detail(self, job_url):
        """Extraire la date de publication depuis la page de détail"""
        try:
            response = self.make_request(job_url)
            if not response:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Mêmes sélecteurs que pour la carte
            date_selectors = [
                'time',
                '.date',
                '.publication-date',
                '.job-date',
                '.offer-date',
                'span[class*="date"]',
                'div[class*="date"]',
                '.timestamp',
                '.time-ago'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    parsed_date = self._parse_date_text(date_text)
                    if parsed_date:
                        return parsed_date
            
            return None
            
        except Exception as e:
            print(f"     ❌ Erreur extraction date détail: {e}")
            return None
    
    def _parse_date_text(self, date_text):
        """Parser le texte de date en objet datetime"""
        try:
            if not date_text:
                return None
                
            date_text = date_text.lower().strip()
            now = datetime.now()
            
            # Formats relatifs
            if 'aujourd\'hui' in date_text or 'today' in date_text:
                return now
            elif 'hier' in date_text or 'yesterday' in date_text:
                return now - timedelta(days=1)
            elif 'il y a' in date_text:
                # Extraire le nombre
                if 'jour' in date_text or 'days' in date_text:
                    days_match = re.search(r'(\d+)\s+jour', date_text)
                    if days_match:
                        days = int(days_match.group(1))
                        return now - timedelta(days=days)
                elif 'heure' in date_text or 'hour' in date_text:
                    hours_match = re.search(r'(\d+)\s+heure', date_text)
                    if hours_match:
                        hours = int(hours_match.group(1))
                        return now - timedelta(hours=hours)
            
            # Formats absolus
            # DD/MM/YYYY ou DD-MM-YYYY
            date_patterns = [
                (r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})', '%d/%m/%Y'),
                (r'(\d{1,2})\s+(\w+)\s+(\d{4})', '%d %B %Y')  # 15 janvier 2024
            ]
            
            for pattern, date_format in date_patterns:
                match = re.search(pattern, date_text)
                if match:
                    try:
                        if date_format == '%d %B %Y':
                            # Gérer les mois français
                            mois_fr = {
                                'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
                                'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
                                'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
                            }
                            jour = int(match.group(1))
                            mois = mois_fr.get(match.group(2).lower())
                            annee = int(match.group(3))
                            if mois:
                                return datetime(annee, mois, jour)
                        else:
                            date_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
                            return datetime.strptime(date_str, date_format)
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            print(f"     ❌ Erreur parsing date '{date_text}': {e}")
            return None

    def _find_job_cards_improved(self, soup):
        """Trouver les cartes d'offres avec une approche améliorée"""
        selectors = [
            'a[href*="/offres/"]',
            'div.job-item',
            'article.job-card',
            'li.job-listing',
            'div.job-listing',
            'article.job-offer',
            'div.offer-card',
            '.job-teaser',
            '.offer-item'
        ]
        
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                print(f"   ✅ Sélecteur '{selector}' -> {len(cards)} éléments")
                real_cards = [card for card in cards if self._is_real_job_card(card)]
                if real_cards:
                    return real_cards
        
        print("   🔍 Recherche par liens d'offres...")
        all_links = soup.find_all('a', href=True)
        job_links = []
        
        for link in all_links:
            href = link['href']
            if '/offres/' in href and len(href) > 10:
                parent_card = self._find_parent_card(link)
                if parent_card and parent_card not in job_links:
                    job_links.append(parent_card)
        
        print(f"   🔗 {len(job_links)} offres trouvées par analyse de liens")
        return job_links
    
    def _is_real_job_card(self, card):
        """Vérifier si c'est une vraie carte d'offre"""
        text = card.get_text(strip=True)
        # CORRECTION : Vérification plus générique pour tous les métiers IT
        return len(text) > 50 and any(keyword in text.lower() for keyword in 
                                    ['développeur', 'developer', 'ingénieur', 'engineer', 'technique', 'software',
                                     'data', 'analyste', 'analyst', 'admin', 'system', 'réseau', 'network',
                                     'cyber', 'sécurité', 'security', 'cloud', 'devops', 'web', 'mobile',
                                     'java', 'python', 'javascript', 'php', 'c#', 'ruby', 'go', 'rust'])
    
    def _find_parent_card(self, element, max_level=5):
        """Trouver le parent contenant qui représente la carte complète"""
        current = element
        for _ in range(max_level):
            current = current.parent
            if current and current.name in ['div', 'article', 'li']:
                classes = current.get('class', [])
                class_str = ' '.join(classes).lower()
                if any(keyword in class_str for keyword in ['card', 'item', 'listing', 'offer', 'job']):
                    return current
                child_count = len([child for child in current.children if child.name and child.get_text(strip=True)])
                if child_count >= 2:
                    return current
        return element.parent
    
    def _analyze_page_structure(self, soup, page_num):
        """Analyser la structure de la page pour debug"""
        print(f"   🔍 ANALYSE DE LA PAGE {page_num}:")
        all_links = soup.find_all('a', href=True)
        job_links = [link for link in all_links if '/offres/' in link['href']]
        print(f"   📊 Total liens: {len(all_links)}")
        print(f"   📊 Liens d'offres: {len(job_links)}")
        
        for i, link in enumerate(job_links[:5]):
            print(f"   🔗 Exemple {i+1}: {link.get_text(strip=True)[:50]} -> {link['href']}")
    
    def _scrape_job_detail_improved(self, job_url, keyword):
        """Scraper la page de détail avec gestion d'erreur améliorée"""
        try:
            response = self.make_request(job_url)
            if not response:
                return {}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            if "accès refusé" in soup.get_text().lower():
                print("      🚫 ACCÈS REFUSÉ sur la page de détail")
                return {}
            
            description = self._extract_description(soup)
            
            return {
                "description_poste": description[:5000],
                "type_contrat": self._extract_contract_type_detail(soup),
                "fourchette_salaire": self._extract_salary(soup),
                "experience_demandee": self._extract_experience(soup),
                "teletravail": self._extract_teletravail(description, soup),
                "competences_mentionnees": self.extract_competences(description),
                "niveau_seniorite": self.extract_seniorite(description, "")
            }
            
        except Exception as e:
            print(f"❌ Erreur détail offre: {e}")
            return {}
    
    def _extract_description(self, soup):
        """Extraire la description avec plusieurs méthodes"""
        selectors = [
            'div.job-description',
            'div.description',
            'article.description',
            'section.description',
            '.job-content',
            '.offer-content',
            'div[class*="description"]',
            'div[class*="content"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        body = soup.find('body')
        return body.get_text(strip=True) if body else ""

    def _extract_contract_type_detail(self, soup):
        try:
            full_text = soup.get_text().lower()
            contract_keywords = {
                'cdi': 'CDI', 'cdd': 'CDD', 'stage': 'Stage',
                'freelance': 'Freelance', 'alternance': 'Alternance', 'intérim': 'Intérim'
            }
            
            for keyword, contract in contract_keywords.items():
                if keyword in full_text:
                    return contract
            return "CDI"
        except:
            return "CDI"
    
    def _extract_salary(self, soup):
        try:
            full_text = soup.get_text()
            salary_pattern = r'(\d+[.,]?\d*)\s*[-à]?\s*(\d+[.,]?\d*)?\s*€?'
            matches = re.findall(salary_pattern, full_text)
            if matches:
                return f"{matches[0][0]} - {matches[0][1]} €" if matches[0][1] else f"{matches[0][0]} €"
            return ""
        except:
            return ""
    
    def _extract_experience(self, soup):
        try:
            full_text = soup.get_text().lower()
            if 'débutant' in full_text or 'junior' in full_text:
                return "Débutant accepté"
            elif 'expérimenté' in full_text or 'senior' in full_text:
                return "Expérimenté"
            elif 'confirmé' in full_text:
                return "Confirmé"
            return ""
        except:
            return ""
    
    def _extract_teletravail(self, description, soup):
        try:
            full_text = (description + " " + soup.get_text()).lower()
            teletravail_keywords = ['télétravail', 'teletravail', 'remote', 'télé travail', 'home office', 'travail à distance']
            for keyword in teletravail_keywords:
                if keyword in full_text:
                    return "Oui"
            return "Non"
        except:
            return "Non"
    
    def extract_competences(self, description):
        if not description:
            return []
        
        competences_techniques = [
            'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin',
            'scala', 'r', 'matlab', 'perl', 'dart', 'html', 'css', 'sass', 'less', 'react', 'angular', 'vue', 'ember', 'svelte',
            'node.js', 'express', 'django', 'flask', 'spring', 'laravel', 'symfony', 'ruby on rails', 'asp.net', 'nestjs',
            'fastapi', 'bootstrap', 'tailwind', 'jquery', 'sql', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlite',
            'mongodb', 'redis', 'cassandra', 'elasticsearch', 'kibana', 'mariaDB', 'dynamodb', 'firebase', 'docker',
            'kubernetes', 'aws', 'azure', 'gcp', 'heroku', 'digital ocean', 'terraform', 'ansible', 'jenkins', 'gitlab',
            'github actions', 'circleci', 'git', 'linux', 'windows', 'agile', 'scrum', 'kanban', 'jira', 'confluence',
            'ci/cd', 'tdd', 'bdd', 'rest api', 'graphql', 'soap', 'microservices', 'serverless', 'lambda', 'machine learning',
            'deep learning', 'ai', 'artificial intelligence', 'data science', 'big data', 'hadoop', 'spark', 'kafka',
            'tableau', 'power bi', 'computer vision', 'nlp', 'natural language processing', 'cybersecurity', 'cryptography',
            'penetration testing', 'ethical hacking', 'owasp', 'vpn', 'firewall', 'android', 'ios', 'react native',
            'flutter', 'xamarin', 'ionic', 'blockchain', 'iot', 'ar/vr', 'augmented reality', 'virtual reality'
        ]
        
        competences_trouvees = []
        desc_lower = description.lower()
        for competence in competences_techniques:
            if competence in desc_lower:
                competences_trouvees.append(competence)
        
        return competences_trouvees
    
    def extract_seniorite(self, description, experience):
        try:
            text_to_analyze = (description + " " + experience).lower()
            
            if any(word in text_to_analyze for word in ['senior', 'expérimenté', 'expert', 'lead', 'principal']):
                return "Senior"
            elif any(word in text_to_analyze for word in ['confirmé', 'expérience', 'mid-level', 'intermédiaire']):
                return "Confirmé"
            elif any(word in text_to_analyze for word in ['junior', 'débutant', 'jeune diplômé', 'entry-level']):
                return "Junior"
            else:
                return "Non spécifié"
        except:
            return "Non spécifié"

def main():
    """Fonction principale de scraping ChooseYourBoss"""
    print("🚀 DÉMARRAGE DU SCRAPING CHOOSEYOURBOSS - 120 DERNIERS JOURS")
    print("=" * 60)
    
    scraper = ChooseYourBossScraper()
    
    # LISTE DES MÉTIERS IT COMPLÈTE
    metiers_it = [
        "développeur", "développeur fullstack", "développeur backend", "développeur frontend",
        "développeur mobile", "développeur web", "ingénieur logiciel", "ingénieur informatique",
        "data scientist", "data analyst", "analyste données", "ingénieur data", "data engineer",
        "machine learning", "deep learning", "intelligence artificielle", "analyste big data",
        "architecte data", "scientifique des données",
        "administrateur système", "administrateur réseau", "devops", "ingénieur devops",
        "cloud engineer", "ingénieur cloud", "spécialiste cloud", "architecte cloud",
        "administrateur cloud",
        "cybersécurité", "analyste sécurité", "ingénieur sécurité", "responsable sécurité informatique",
        "ethical hacker", "pentester",
        "webmaster", "designer UX/UI", "intégrateur web", "développeur javascript",
        "développeur python", "développeur java", "développeur c#", "développeur php",
        "administrateur base de données", "DBA", "ingénieur systèmes", "technicien informatique",
        "support technique", "helpdesk",
        "chef de projet informatique", "consultant informatique", "product owner", "scrum master",
        "analyste fonctionnel", "testeur QA", "ingénieur qualité logiciel"
    ]
    
    all_offers = []
    total_metiers = len(metiers_it)
    
    print(f"🎯 {total_metiers} MÉTIERS À SCRAPER")
    print("=" * 60)
    
    for index, metier in enumerate(metiers_it, 1):
        print(f"\n📊 [{index}/{total_metiers}] RECHERCHE: '{metier.upper()}'")
        print("-" * 50)
        
        # Pause plus longue entre les métiers pour éviter le blocage
        if index > 1:
            pause_metier = random.uniform(15, 25)
            print(f"💤 Pause de {pause_metier:.1f} secondes entre les métiers...")
            time.sleep(pause_metier)
        
        # Utiliser la nouvelle méthode pour les 120 derniers jours
        offers = scraper.scrape_search_last_120_days(keyword=metier, max_pages=2)  # Réduit à 2 pages pour tester
        
        if offers:
            all_offers.extend(offers)
            print(f"✅ {len(offers)} offres récentes collectées pour '{metier}'")
        else:
            print(f"⚠️ Aucune offre récente trouvée pour '{metier}'")
        
        # Sauvegarde intermédiaire après chaque métier
        if all_offers:
            PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            DATA_DIR = os.path.join(PROJECT_ROOT, "data", "scraped")
            os.makedirs(DATA_DIR, exist_ok=True)
            
            # Sauvegarde temporaire
            temp_json_path = os.path.join(DATA_DIR, f'offres_it_chooseyourboss_temp.json')
            with open(temp_json_path, 'w', encoding='utf-8') as f:
                json.dump(all_offers, f, ensure_ascii=False, indent=2)
            print(f"💾 Sauvegarde temporaire: {len(all_offers)} offres")
    
    # Sauvegarde finale des résultats
    if all_offers:
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DATA_DIR = os.path.join(PROJECT_ROOT, "data", "scraped")
        os.makedirs(DATA_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(DATA_DIR, f'offres_it_chooseyourboss.json')
        csv_path = os.path.join(DATA_DIR, f'offres_it_chooseyourboss.csv')
        
        # Sauvegarde JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=2)
        
        # Sauvegarde CSV
        df = pd.DataFrame(all_offers)
        df['competences_mentionnees'] = df['competences_mentionnees'].apply(lambda x: ', '.join(x) if x else '')
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        # Statistiques détaillées
        dates_publication = [datetime.fromisoformat(offer['date_publication_reelle']) for offer in all_offers]
        plus_ancienne = min(dates_publication) if dates_publication else None
        plus_recente = max(dates_publication) if dates_publication else None
        
        # Compter les offres par métier
        offres_par_metier = {}
        for offer in all_offers:
            metier = offer['metier_recherche']
            offres_par_metier[metier] = offres_par_metier.get(metier, 0) + 1
        
        print(f"\n{'='*60}")
        print("📊 RAPPORT FINAL DE COLLECTE")
        print(f"{'='*60}")
        print(f"💾 TOTAL OFFRES COLLECTÉES: {len(all_offers)}")
        print(f"📅 PÉRIODE COUVERTE: {plus_ancienne.strftime('%d/%m/%Y') if plus_ancienne else 'N/A'} - {plus_recente.strftime('%d/%m/%Y') if plus_recente else 'N/A'}")
        print(f"🎯 MÉTIERS AVEC OFFRES: {len(offres_par_metier)}/{total_metiers}")
        
        print(f"\n📈 RÉPARTITION PAR MÉTIER:")
        for metier, count in sorted(offres_par_metier.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {metier}: {count} offres")
        
        print(f"\n📁 FICHIERS SAUVEGARDÉS:")
        print(f"   - JSON: {os.path.basename(json_path)}")
        print(f"   - CSV: {os.path.basename(csv_path)}")
        
    else:
        print("\n❌ Aucune offre récente collectée sur aucun métier")

if __name__ == "__main__":
    main()