import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
import time
from typing import List, Dict
import os 
import csv

class ApecITScraper:
    def __init__(self):
        self.base_url = "https://www.apec.fr"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Liste étendue des compétences IT
        self.competences_it = [
            # Langages de programmation
            'python', 'java', 'javascript', 'typescript', 'c#', 'c++', 'c', 'php', 'ruby', 'go', 'rust', 'scala', 'kotlin', 'swift',
            'r', 'dart', 'perl', 'html', 'css', 'sass', 'less',
            
            # Frameworks et bibliothèques
            'react', 'angular', 'vue', 'node.js', 'spring', 'django', 'flask', 'laravel', 'symfony', 'express', 'nestjs',
            'react native', 'flutter', 'xamarin', 'ionic', 'cordova',
            'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy',
            'hadoop', 'spark', 'kafka', 'airflow', 'dbt', 'talend', 'informatica',
            
            # Bases de données
            'sql', 'mysql', 'postgresql', 'oracle', 'sql server', 'mongodb', 'redis', 'cassandra', 'elasticsearch',
            'dynamodb', 'cosmosdb', 'snowflake', 'bigquery', 'redshift',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab', 'github actions', 'terraform', 'ansible',
            'ci/cd', 'devops', 'git', 'linux', 'windows server', 'nginx', 'apache',
            
            # Métiers et domaines
            'machine learning', 'deep learning', 'ai', 'intelligence artificielle', 'computer vision', 'nlp',
            'data science', 'data analyst', 'data engineer', 'business intelligence', 'bi', 'etl', 'data warehouse',
            'cybersécurité', 'sécurité', 'pentest', 'soc', 'siem', 'iso 27001', 'rgpd',
            'développement mobile', 'android', 'ios', 'mobile',
            'jeux vidéo', 'unity', 'unreal engine', 'game development',
            'frontend', 'backend', 'fullstack', 'web development',
            'agile', 'scrum', 'kanban', 'safe',
            
            # Outils
            'power bi', 'tableau', 'qlik', 'jira', 'confluence', 'figma', 'sketch', 'adobe xd',
            'excel', 'vba', 'word', 'powerpoint'
        ]

    def determiner_metier(self, titre: str, description: str) -> str:
        """Détermine le métier principal basé sur le titre et la description"""
        texte = f"{titre} {description}".lower()
        
        categories_metiers = {
            "développement": ['développeur', 'developer', 'dev', 'programmeur', 'ingénieur développement', 'software engineer', 'code'],
            "data": ['data', 'data scientist', 'data analyst', 'data engineer', 'bi', 'business intelligence', 'etl', 'data warehouse'],
            "intelligence artificielle": ['ai', 'artificial intelligence', 'machine learning', 'deep learning', 'nlp', 'computer vision'],
            "cybersécurité": ['cybersécurité', 'security', 'sécurité', 'pentest', 'soc', 'sécurité informatique', 'cyber'],
            "développement mobile": ['mobile', 'android', 'ios', 'react native', 'flutter', 'mobile developer'],
            "jeux vidéo": ['jeux vidéo', 'game', 'unity', 'unreal engine', 'game developer'],
            "devops": ['devops', 'sre', 'site reliability', 'infrastructure', 'cloud engineer'],
            "frontend": ['frontend', 'front-end', 'react', 'angular', 'vue', 'javascript', 'typescript'],
            "backend": ['backend', 'back-end', 'server', 'api', 'microservices'],
            "fullstack": ['fullstack', 'full-stack'],
            "administration": ['admin', 'administrateur', 'system', 'réseau', 'network', 'linux', 'windows server']
        }
        
        scores = {metier: 0 for metier in categories_metiers.keys()}
        
        for metier, mots_cles in categories_metiers.items():
            for mot in mots_cles:
                if mot in texte:
                    scores[metier] += 1
        
        # Retourner le métier avec le score le plus élevé
        metier_principal = max(scores.items(), key=lambda x: x[1])
        return metier_principal[0] if metier_principal[1] > 0 else "informatique"

    def extraire_competences(self, texte: str) -> List[str]:
        """Extrait les compétences mentionnées dans le texte"""
        texte_lower = texte.lower()
        competences_trouvees = []
        
        for competence in self.competences_it:
            if competence in texte_lower:
                competences_trouvees.append(competence)
                
        return list(set(competences_trouvees))

    def parser_date(self, date_str: str) -> str:
        """Parse la date de publication"""
        try:
            if "aujourd'hui" in date_str.lower():
                return datetime.now().isoformat()
            elif "hier" in date_str.lower():
                return (datetime.now() - timedelta(days=1)).isoformat()
            else:
                for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d %b %Y']:
                    try:
                        return datetime.strptime(date_str.strip(), fmt).isoformat()
                    except:
                        continue
                return datetime.now().isoformat()
        except:
            return datetime.now().isoformat()

    def extraire_salaire(self, description: str) -> str:
        """Extrait la fourchette salariale de la description"""
        patterns = [
            r'(\d{2,5}\s*€?\s*à\s*\d{2,5}\s*€?)',
            r'(\d{2,5}\s*-\s*\d{2,5}\s*€?)',
            r'salaire.*?(\d{2,5}).*?(\d{2,5})',
            r'(\d{2,5}\s*K\s*à\s*\d{2,5}\s*K)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description.lower())
            if match:
                salaire = match.group(1).replace('k', '000').replace(' ', '')
                return f"Annuel de {salaire} Euros"
        
        return "Non précisé"

    def determiner_seniorite(self, titre: str, description: str) -> str:
        """Détermine le niveau de séniorité"""
        texte = f"{titre} {description}".lower()
        
        if any(mot in texte for mot in ['junior', 'débutant', 'jeune diplômé', 'bac+', 'stage', 'alternance']):
            return "Junior"
        elif any(mot in texte for mot in ['senior', 'expert', 'lead', 'principal', 'architecte']):
            return "Senior"
        elif any(mot in texte for mot in ['confirmé', 'expérience', '3 ans', '5 ans', 'expérimenté']):
            return "Confirmé"
        else:
            return "Non précisé"

    def scraper_offres_apec(self, mot_cle: str = "informatique") -> List[Dict]:
        """Scrape les offres d'emploi de l'APEC avec la bonne URL"""
        offres = []
        
        # URL corrigée pour l'APEC
        url_recherche = f"{self.base_url}/candidat/recherche-emploi.html?keywords={mot_cle.replace(' ', '+')}"
        
        try:
            print(f"🌐 Accès à: {url_recherche}")
            response = self.session.get(url_recherche, timeout=10)
            response.raise_for_status()
            
            # Vérifier si nous avons été redirigés ou bloqués
            if response.url != url_recherche:
                print(f"⚠️ Redirection vers: {response.url}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Vérifier si nous avons une page de résultats valide
            titre_page = soup.find('title')
            if titre_page:
                print(f"📄 Page chargée: {titre_page.get_text()}")
            
            # Nouveaux sélecteurs pour l'APEC
            offres_cartes = soup.find_all('div', class_=['offer-list__item', 'result-list__item', 'offer-card'])
            
            if not offres_cartes:
                # Essayer d'autres sélecteurs courants
                offres_cartes = soup.find_all('article', class_=['offer', 'job-offer'])
                if not offres_cartes:
                    offres_cartes = soup.find_all('li', class_=['offer-item', 'job-item'])
            
            print(f"🔍 {len(offres_cartes)} offres trouvées sur la page")
            
            for i, carte in enumerate(offres_cartes):
                try:
                    print(f"📝 Traitement de l'offre {i+1}/{len(offres_cartes)}")
                    offre_data = self.parser_carte_offre(carte)
                    if offre_data:
                        offres.append(offre_data)
                        print(f"✅ Offre ajoutée: {offre_data['intitule_poste'][:50]}...")
                    
                    time.sleep(1)  # Respectful delay
                    
                except Exception as e:
                    print(f"❌ Erreur lors du parsing d'une offre: {e}")
                    continue
                    
        except requests.exceptions.RequestException as e:
            print(f"🚨 Erreur réseau lors du scraping: {e}")
        except Exception as e:
            print(f"🚨 Erreur inattendue lors du scraping: {e}")
            
        return offres

    def parser_carte_offre(self, carte) -> Dict:
        """Parse une carte d'offre individuelle"""
        try:
            # Titre du poste - sélecteurs mis à jour
            titre_element = carte.find(['h2', 'h3', 'a'], class_=['offer-card__title', 'result-list__title', 'offer-title', 'job-title'])
            if not titre_element:
                titre_element = carte.find(['h2', 'h3', 'a'])
            titre = titre_element.get_text(strip=True) if titre_element else "Non précisé"
            
            # Entreprise
            entreprise_element = carte.find(['span', 'div'], class_=['offer-card__company', 'company-name', 'employer'])
            entreprise = entreprise_element.get_text(strip=True) if entreprise_element else "Non précisé"
            
            # Localisation
            localisation_element = carte.find(['span', 'div'], class_=['offer-card__location', 'location', 'workplace'])
            localisation = localisation_element.get_text(strip=True) if localisation_element else "Non précisé"
            
            # Date de publication
            date_element = carte.find(['span', 'div'], class_=['offer-card__date', 'date', 'publication-date'])
            date_publication = self.parser_date(date_element.get_text(strip=True)) if date_element else datetime.now().isoformat()
            
            # Lien vers l'offre détaillée
            lien_element = carte.find('a', href=True)
            if lien_element and lien_element.get('href'):
                lien_relatif = lien_element['href']
                lien_complet = f"{self.base_url}{lien_relatif}" if lien_relatif.startswith('/') else lien_relatif
            else:
                lien_complet = ""
            
            # Récupérer les détails complets depuis la page de l'offre
            details_offre = self.scraper_details_offre(lien_complet) if lien_complet else {}
            description_complete = details_offre.get('description', '')
            
            # Générer un ID d'offre unique
            id_offre = str(hash(f"{titre}{entreprise}{lien_complet}"))[-10:] if lien_complet else str(hash(f"{titre}{entreprise}"))[-10:]
            
            # Construire l'objet final
            offre = {
                "intitule_poste": titre,
                "nom_entreprise": entreprise,
                "ville_region": localisation,
                "date_publication": date_publication,
                "type_contrat": details_offre.get('type_contrat', 'Non précisé'),
                "experience_demandee": details_offre.get('experience', 'Non précisé'),
                "niveau_seniorite": self.determiner_seniorite(titre, description_complete),
                "description_poste": description_complete,
                "source_offre": lien_complet,
                "teletravail": details_offre.get('teletravail', 'Non'),
                "competences_mentionnees": self.extraire_competences(description_complete + ' ' + titre),
                "fourchette_salaire": self.extraire_salaire(description_complete),
                "metier_recherche": self.determiner_metier(titre, description_complete),
                "id_offre": id_offre
            }
            
            return offre
            
        except Exception as e:
            print(f"❌ Erreur dans parser_carte_offre: {e}")
            return None

    def scraper_details_offre(self, url: str) -> Dict:
        """Scrape les détails d'une offre spécifique"""
        details = {}
        
        try:
            if not url:
                return details
                
            print(f"🔍 Accès aux détails: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Description complète - sélecteurs mis à jour
            description_element = soup.find('div', class_=['offer-description', 'description-content', 'job-description'])
            if not description_element:
                description_element = soup.find('section', class_=['description', 'content'])
            
            details['description'] = description_element.get_text(strip=True) if description_element else ""
            
            # Type de contrat
            for element in soup.find_all(['span', 'div', 'li']):
                texte = element.get_text(strip=True).lower()
                if any(mot in texte for mot in ['cdi', 'cdd', 'stage', 'alternance', 'freelance', 'contrat à durée']):
                    details['type_contrat'] = element.get_text(strip=True)
                    break
            else:
                details['type_contrat'] = 'Non précisé'
            
            # Expérience
            for element in soup.find_all(['span', 'div', 'li']):
                texte = element.get_text(strip=True).lower()
                if any(mot in texte for mot in ['expérience', 'année', 'ans', 'expérimenté', 'débutant']):
                    details['experience'] = element.get_text(strip=True)
                    break
            else:
                details['experience'] = 'Non précisé'
            
            # Télétravail
            texte_complet = details['description'].lower()
            details['teletravail'] = "Oui" if any(mot in texte_complet for mot in ['télétravail', 'remote', 'teletravail', 'travail à distance']) else "Non"
            
        except Exception as e:
            print(f"❌ Erreur lors du scraping des détails {url}: {e}")
            
        return details

    def sauvegarder_json(self, offres: List[Dict], filename: str = "offres_it_apec.json"):
        """Sauvegarde les offres en JSON"""
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DATA_DIR = os.path.join(PROJECT_ROOT, "data", "scraped")
        os.makedirs(DATA_DIR, exist_ok=True)
        json_path = os.path.join(DATA_DIR, filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(offres, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Données JSON sauvegardées dans: {json_path}")
        return json_path

    def sauvegarder_csv(self, offres: List[Dict], filename: str = "offres_it_apec.csv"):
        """Sauvegarde les offres en CSV"""
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DATA_DIR = os.path.join(PROJECT_ROOT, "data", "scraped")
        os.makedirs(DATA_DIR, exist_ok=True)
        csv_path = os.path.join(DATA_DIR, filename)
        
        if offres:
            # Préparer les headers du CSV
            fieldnames = offres[0].keys()
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for offre in offres:
                    # Convertir la liste de compétences en string pour le CSV
                    offre_csv = offre.copy()
                    offre_csv['competences_mentionnees'] = ', '.join(offre['competences_mentionnees'])
                    writer.writerow(offre_csv)
            
            print(f"✅ Données CSV sauvegardées dans: {csv_path}")
        else:
            print("❌ Aucune donnée à sauvegarder en CSV")
        
        return csv_path

# Utilisation du scraper
if __name__ == "__main__":
    scraper = ApecITScraper()
    
    print("🚀 Début du scraping de toutes les offres IT sur l'APEC...")
    
    # Mots-clés couvrant tous les domaines IT - version simplifiée pour tester
    mots_cles = [
        "informatique",
        "développeur",
        "data",
        "cybersécurité",
        "devops",
        "cloud"
    ]
    
    toutes_offres = []
    
    for mot_cle in mots_cles:
        print(f"\n🔎 Recherche: '{mot_cle}'")
        offres = scraper.scraper_offres_apec(mot_cle)
        toutes_offres.extend(offres)
        print(f"📊 Trouvées: {len(offres)} offres")
        time.sleep(3)  # Pause plus longue entre les recherches
    
    # Supprimer les doublons
    offres_uniques = {offre['id_offre']: offre for offre in toutes_offres if offre is not None}.values()
    offres_liste = list(offres_uniques)
    
    print(f"\n📈 Total d'offres IT uniques: {len(offres_liste)}")
    
    if offres_liste:
        # Statistiques par métier
        metiers_count = {}
        for offre in offres_liste:
            metier = offre['metier_recherche']
            metiers_count[metier] = metiers_count.get(metier, 0) + 1
        
        print("\n📊 Statistiques par domaine:")
        for metier, count in sorted(metiers_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {metier}: {count} offres")
        
        # Sauvegarder en JSON et CSV
        json_path = scraper.sauvegarder_json(offres_liste, "offres_it_apec.json")
        csv_path = scraper.sauvegarder_csv(offres_liste, "offres_it_apec.csv")
        
        # Afficher le résumé final
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        DATA_DIR = os.path.join(PROJECT_ROOT, "data", "scraped")
        
        print(f"\n🎉 Scraping terminé avec succès!")
        print(f"📁 Dossier des données: {DATA_DIR}")
        print(f"📄 Fichier JSON: {os.path.basename(json_path)}")
        print(f"📊 Fichier CSV: {os.path.basename(csv_path)}")
        print(f"🔢 Total d'offres: {len(offres_liste)}")
    else:
        print("\n❌ Aucune offre trouvée. Vérifiez:")
        print("   - Votre connexion Internet")
        print("   - Les sélecteurs CSS (l'APEC a peut-être changé son design)")
        print("   - Les restrictions d'accès (CAPTCHA, blocage IP)")