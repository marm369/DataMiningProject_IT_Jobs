import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
from datetime import datetime, timedelta
import json
import os
import re
from urllib.parse import urljoin

class ChooseYourBossScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.base_url = "https://www.chooseyourboss.com"
        
    def scrape_search(self, keyword="développeur", max_pages=3):
        """Scraper la page de recherche de ChooseYourBoss"""
        all_offers = []
        
        for page in range(1, max_pages + 1):
            print(f"🔍 Page {page} pour '{keyword}'...")
            
            # URL de recherche
            search_url = f"{self.base_url}/offres/emploi?q={keyword.replace(' ', '+')}&p={page}"
            
            try:
                response = self.session.get(search_url, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                job_cards = soup.find_all('article', class_='job')
                
                if not job_cards:
                    print(f"  ➤ Aucune offre trouvée sur la page {page}")
                    break
                
                print(f"  📄 {len(job_cards)} offres trouvées sur cette page")
                
                for i, card in enumerate(job_cards, 1):
                    print(f"    📋 Traitement offre {i}/{len(job_cards)}")
                    offer = self._parse_job_card(card, keyword)
                    if offer:
                        all_offers.append(offer)
                    
                    # Pause entre les offres
                    time.sleep(random.uniform(1, 2))
                
                # Pause entre les pages
                time.sleep(random.uniform(2, 4))
                
            except Exception as e:
                print(f"❌ Erreur sur la page {page}: {e}")
                continue
        
        return all_offers
    
    def _parse_job_card(self, card, keyword):
        """Parser une carte d'offre d'emploi"""
        try:
            # Titre du poste
            title_elem = card.find('h2', class_='title')
            if not title_elem:
                return None
                
            title = title_elem.get_text(strip=True)
            
            # Lien vers l'offre
            link_elem = card.find('a', href=True)
            if not link_elem:
                return None
                
            job_url = urljoin(self.base_url, link_elem['href'])
            
            # Entreprise
            company_elem = card.find('span', class_='company')
            company = company_elem.get_text(strip=True) if company_elem else ""
            
            # Localisation
            location_elem = card.find('span', class_='location')
            location = location_elem.get_text(strip=True) if location_elem else ""
            
            # Date de publication
            date_elem = card.find('time')
            publication_date = date_elem.get('datetime', '') if date_elem else ""
            
            # Type de contrat (à extraire des tags)
            contract_type = self._extract_contract_type(card)
            
            # Récupérer les détails complets depuis la page de l'offre
            detail_offer = self._scrape_job_detail(job_url, keyword)
            
            if detail_offer:
                offer = {
                    "intitule_poste": title,
                    "nom_entreprise": company,
                    "ville_region": location,
                    "date_publication": publication_date or datetime.now().isoformat(),
                    "type_contrat": contract_type,
                    "experience_demandee": detail_offer.get("experience_demandee", ""),
                    "niveau_seniorite": detail_offer.get("niveau_seniorite", "Non spécifié"),
                    "description_poste": detail_offer.get("description_poste", ""),
                    "source_offre": job_url,
                    "teletravail": detail_offer.get("teletravail", "Non"),
                    "competences_mentionnees": detail_offer.get("competences_mentionnees", []),
                    "fourchette_salaire": detail_offer.get("fourchette_salaire", ""),
                    "metier_recherche": keyword,
                    "id_offre": job_url.split('/')[-1],
                    "date_collecte": datetime.now().isoformat()
                }
                return offer
            else:
                return None
                
        except Exception as e:
            print(f"❌ Erreur parsing carte: {e}")
            return None
    
    def _scrape_job_detail(self, job_url, keyword):
        """Scraper la page de détail d'une offre"""
        try:
            print(f"      📖 Extraction des détails: {job_url}")
            response = self.session.get(job_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Description complète
            description_elem = soup.find('div', class_='description')
            description = description_elem.get_text(strip=True) if description_elem else ""
            
            # Salaire
            salary = self._extract_salary(soup)
            
            # Expérience demandée
            experience = self._extract_experience(soup)
            
            # Télétravail
            teletravail = self._extract_teletravail(description, soup)
            
            # Compétences
            competences = self.extract_competences(description)
            
            # Niveau de séniorité
            seniorite = self.extract_seniorite(description, experience)
            
            return {
                "description_poste": description,
                "fourchette_salaire": salary,
                "experience_demandee": experience,
                "teletravail": teletravail,
                "competences_mentionnees": competences,
                "niveau_seniorite": seniorite
            }
            
        except Exception as e:
            print(f"❌ Erreur détail offre: {e}")
            return {}
    
    def _extract_contract_type(self, card):
        """Extraire le type de contrat depuis les tags"""
        try:
            tags_elem = card.find('ul', class_='tags')
            if tags_elem:
                tags = [tag.get_text(strip=True) for tag in tags_elem.find_all('li')]
                contract_keywords = ['CDI', 'CDD', 'Stage', 'Freelance', 'Alternance', 'Intérim']
                for tag in tags:
                    for keyword in contract_keywords:
                        if keyword.lower() in tag.lower():
                            return keyword
            return "CDI"  # Valeur par défaut
        except:
            return "CDI"
    
    def _extract_salary(self, soup):
        """Extraire la fourchette salariale"""
        try:
            # Chercher dans les éléments de détail
            details = soup.find_all('div', class_='detail')
            for detail in details:
                text = detail.get_text(strip=True)
                if any(word in text.lower() for word in ['salaire', 'rémunération', '€', 'euros']):
                    return text
            
            # Chercher dans tout le texte
            full_text = soup.get_text()
            salary_pattern = r'(\d+[.,]?\d*)\s*[-à]?\s*(\d+[.,]?\d*)?\s*€?'
            matches = re.findall(salary_pattern, full_text)
            if matches:
                return f"{matches[0][0]} - {matches[0][1]} €" if matches[0][1] else f"{matches[0][0]} €"
            
            return ""
        except:
            return ""
    
    def _extract_experience(self, soup):
        """Extraire l'expérience demandée"""
        try:
            details = soup.find_all('div', class_='detail')
            for detail in details:
                text = detail.get_text(strip=True)
                if any(word in text.lower() for word in ['expérience', 'expérimenté', 'débutant', 'junior', 'senior']):
                    return text
            
            return ""
        except:
            return ""
    
    def _extract_teletravail(self, description, soup):
        """Détecter la possibilité de télétravail"""
        try:
            full_text = description + " " + soup.get_text()
            teletravail_keywords = ['télétravail', 'teletravail', 'remote', 'télé travail', 'home office', 'travail à distance']
            for keyword in teletravail_keywords:
                if keyword in full_text.lower():
                    return "Oui"
            return "Non"
        except:
            return "Non"
    
    def extract_competences(self, description):
        """Extraire les compétences techniques de la description"""
        if not description:
            return []
        
        competences_techniques = [
            # Langages de programmation
            'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin',
            'scala', 'r', 'matlab', 'perl', 'dart', 'html', 'css', 'sass', 'less',
            
            # Frameworks et bibliothèques
            'react', 'angular', 'vue', 'ember', 'svelte', 'node.js', 'express', 'django', 'flask', 'spring', 'laravel',
            'symfony', 'ruby on rails', 'asp.net', 'nestjs', 'fastapi', 'bootstrap', 'tailwind', 'jquery',
            
            # Bases de données
            'sql', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlite', 'mongodb', 'redis',
            'cassandra', 'elasticsearch', 'kibana', 'mariaDB', 'dynamodb', 'firebase',
            
            # Cloud et DevOps
            'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'heroku', 'digital ocean', 'terraform',
            'ansible', 'jenkins', 'gitlab', 'github actions', 'circleci', 'git', 'linux', 'windows',
            
            # Méthodologies
            'agile', 'scrum', 'kanban', 'jira', 'confluence', 'ci/cd', 'tdd', 'bdd',
            
            # Technologies spécifiques
            'rest api', 'graphql', 'soap', 'microservices', 'serverless', 'lambda',
            'machine learning', 'deep learning', 'ai', 'artificial intelligence',
            'data science', 'big data', 'hadoop', 'spark', 'kafka', 'tableau', 'power bi',
            'computer vision', 'nlp', 'natural language processing',
            
            # Sécurité
            'cybersecurity', 'cryptography', 'penetration testing', 'ethical hacking',
            'owasp', 'vpn', 'firewall',
            
            # Mobiles
            'android', 'ios', 'react native', 'flutter', 'xamarin', 'ionic',
            
            # Autres
            'blockchain', 'iot', 'ar/vr', 'augmented reality', 'virtual reality'
        ]
        
        competences_trouvees = []
        desc_lower = description.lower()
        for competence in competences_techniques:
            if competence in desc_lower:
                competences_trouvees.append(competence)
        
        return competences_trouvees
    
    def extract_seniorite(self, description, experience):
        """Extraire le niveau de séniorité"""
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
    print("🚀 DÉMARRAGE DU SCRAPING CHOOSEYOURBOSS")
    print("=" * 60)
    
    scraper = ChooseYourBossScraper()
    
    # Liste des métiers IT à rechercher
    metiers_it = [
        "développeur", "data scientist", "devops", "ingénieur logiciel",
        "administrateur réseau", "cybersécurité", "cloud engineer"
    ]
    
    all_offers = []
    
    for metier in metiers_it:
        print(f"\n🎯 RECHERCHE: '{metier.upper()}'")
        print("-" * 40)
        
        offers = scraper.scrape_search(keyword=metier, max_pages=2)
        
        if offers:
            all_offers.extend(offers)
            print(f"✅ {len(offers)} offres collectées pour '{metier}'")
        else:
            print(f"⚠️ Aucune offre trouvée pour '{metier}'")
        
        # Pause plus longue entre les métiers
        if metier != metiers_it[-1]:
            pause_time = random.uniform(10, 15)
            print(f"💤 Pause de {pause_time:.1f} secondes...")
            time.sleep(pause_time)
    
    # Sauvegarde des résultats
    if all_offers:
        # Détecter le répertoire racine du projet
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DATA_DIR = os.path.join(PROJECT_ROOT, "data", "scraped")
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Fichiers de sortie
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = os.path.join(DATA_DIR, f'offres_chooseyourboss_{timestamp}.json')
        csv_path = os.path.join(DATA_DIR, f'offres_chooseyourboss_{timestamp}.csv')
        
        # Sauvegarde JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_offers, f, ensure_ascii=False, indent=2)
        
        # Sauvegarde CSV
        df = pd.DataFrame(all_offers)
        df['competences_mentionnees'] = df['competences_mentionnees'].apply(lambda x: ', '.join(x) if x else '')
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        # Métadonnées
        metadata = {
            "date_collecte": datetime.now().isoformat(),
            "site_source": "ChooseYourBoss",
            "total_offres": len(all_offers),
            "metiers_recherches": metiers_it,
            "colonnes_disponibles": list(all_offers[0].keys()) if all_offers else []
        }
        
        meta_path = os.path.join(DATA_DIR, f'metadata_chooseyourboss_{timestamp}.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 60)
        print("💾 DONNÉES SAUVEGARDÉES AVEC SUCCÈS!")
        print("=" * 60)
        print(f"📁 Emplacement: {DATA_DIR}")
        print(f"📄 JSON: {os.path.basename(json_path)}")
        print(f"📄 CSV: {os.path.basename(csv_path)}")
        print(f"📄 Métadonnées: {os.path.basename(meta_path)}")
        
        # Statistiques
        print(f"\n📊 STATISTIQUES DE LA COLLECTE:")
        print(f"   - Total offres: {len(all_offers)}")
        print(f"   - Métiers recherchés: {len(metiers_it)}")
        print(f"   - Colonnes extraites: {len(metadata['colonnes_disponibles'])}")
        
        # Aperçu des 3 premières offres
        if len(all_offers) >= 3:
            print(f"\n👀 APERÇU DES DONNÉES (3 premières offres):")
            for i, offer in enumerate(all_offers[:3], 1):
                print(f"   {i}. {offer['intitule_poste']} - {offer['nom_entreprise']}")
                print(f"      📍 {offer['ville_region']} | 🏢 {offer['type_contrat']}")
                print(f"      💻 {len(offer['competences_mentionnees'])} compétences trouvées")
                print()
                
    else:
        print("❌ Aucune offre collectée")

if __name__ == "__main__":
    main()