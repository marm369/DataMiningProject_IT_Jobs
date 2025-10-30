import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime
import os

def scrape_accessible_sites():
    """
    Scraping de sites plus accessibles que Indeed
    """
    print("🔍 DÉMARRAGE SCRAPING SITES ACCESSIBLES...")
    print("=" * 60)
    
    all_offers = []
    
    # 1. LinkedIn (version simplifiée)
    print("\n1. 💼 TENTATIVE LINKEDIN...")
    linkedin_offers = scrape_linkedin_simple()
    all_offers.extend(linkedin_offers)
    print(f"✅ LinkedIn: {len(linkedin_offers)} offres")
    
    # 2. Glassdoor (version simplifiée)
    print("\n2. 🏢 TENTATIVE GLASSDOOR...")
    glassdoor_offers = scrape_glassdoor_simple()
    all_offers.extend(glassdoor_offers)
    print(f"✅ Glassdoor: {len(glassdoor_offers)} offres")
    
    # 3. ChooseYourBoss (startups françaises)
    print("\n3. 🚀 TENTATIVE CHOOSEYOURBOSS...")
    cyb_offers = scrape_chooseyourboss()
    all_offers.extend(cyb_offers)
    print(f"✅ ChooseYourBoss: {len(cyb_offers)} offres")
    
    return all_offers

def scrape_linkedin_simple():
    """Scraping LinkedIn simplifié"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
    }
    
    offers = []
    
    # URLs de recherche LinkedIn
    linkedin_urls = [
        "https://www.linkedin.com/jobs/search/?keywords=stage%20informatique&location=France",
        "https://www.linkedin.com/jobs/search/?keywords=alternance%20informatique&location=France"
    ]
    
    for url in linkedin_urls:
        try:
            print(f"   🔍 Recherche: {url.split('=')[1].split('&')[0].replace('%20', ' ')}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Sélecteurs LinkedIn basiques
                job_elements = soup.find_all('div', class_=['base-search-card__info', 'job-search-card'])
                
                for job_elem in job_elements[:8]:  # Limiter à 8 offres
                    offer = parse_linkedin_element(job_elem, url)
                    if offer:
                        offers.append(offer)
                
            time.sleep(3)
            
        except Exception as e:
            print(f"   ❌ Erreur LinkedIn: {e}")
    
    return offers

def parse_linkedin_element(element, url):
    """Parser un élément LinkedIn"""
    try:
        # Titre
        title_elem = element.find(['h3', 'a'], class_=['base-search-card__title', 'job-title'])
        title = title_elem.get_text(strip=True) if title_elem else "Stage/Alternance Informatique"
        
        # Entreprise
        company_elem = element.find(['h4', 'a'], class_=['base-search-card__subtitle', 'company-name'])
        company = company_elem.get_text(strip=True) if company_elem else "Entreprise IT"
        
        # Localisation
        location_elem = element.find(['span', 'div'], class_=['job-search-card__location', 'location'])
        location = location_elem.get_text(strip=True) if location_elem else "France"
        
        contract_type = "Stage" if "stage" in url else "Alternance"
        
        return {
            'Intitulé du poste': title,
            'Nom de l entreprise': company,
            'Ville ou région': location,
            'Date de publication': datetime.now().strftime("%d/%m/%Y"),
            'Type de contrat': contract_type,
            'Nombre d années d expérience demandées': '0',
            'Niveau de seniorité': 'Étudiant',
            'Description du poste': f"Offre LinkedIn - {title} chez {company}",
            'Source': 'LinkedIn',
            'Télétravail': 'Non spécifié',
            'Compétences mentionnées': extract_skills_from_title(title),
            'Fourchette salariale': 'Non spécifié',
            'URL': url
        }
    except Exception as e:
        print(f"   ⚠ Erreur parsing LinkedIn: {e}")
        return None

def scrape_glassdoor_simple():
    """Scraping Glassdoor simplifié"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    offers = []
    
    # URLs Glassdoor
    glassdoor_urls = [
        "https://www.glassdoor.fr/Emploi/stage-informatique-emplois-SRCH_KO0,18.htm",
        "https://www.glassdoor.fr/Emploi/alternance-informatique-emplois-SRCH_KO0,20.htm"
    ]
    
    for url in glassdoor_urls:
        try:
            search_type = "Stage" if "stage" in url else "Alternance"
            print(f"   🔍 Recherche: {search_type}")
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Sélecteurs Glassdoor
                job_cards = soup.find_all('li', class_=['react-job-listing', 'jobListing'])
                
                for card in job_cards[:6]:  # Limiter à 6 offres
                    offer = parse_glassdoor_card(card, search_type)
                    if offer:
                        offers.append(offer)
                
            time.sleep(4)
            
        except Exception as e:
            print(f"   ❌ Erreur Glassdoor: {e}")
    
    return offers

def parse_glassdoor_card(card, contract_type):
    """Parser une carte Glassdoor"""
    try:
        # Titre
        title_elem = card.find(['a', 'h3'], class_=['jobLink', 'job-title'])
        title = title_elem.get_text(strip=True) if title_elem else f"{contract_type} Informatique"
        
        # Entreprise
        company_elem = card.find(['span', 'div'], class_=['employer-name', 'company'])
        company = company_elem.get_text(strip=True) if company_elem else "Entreprise Tech"
        
        # Localisation
        location_elem = card.find(['span', 'div'], class_=['location', 'loc'])
        location = location_elem.get_text(strip=True) if location_elem else "France"
        
        return {
            'Intitulé du poste': title,
            'Nom de l entreprise': company,
            'Ville ou région': location,
            'Date de publication': datetime.now().strftime("%d/%m/%Y"),
            'Type de contrat': contract_type,
            'Nombre d années d expérience demandées': '0',
            'Niveau de seniorité': 'Junior',
            'Description du poste': f"Offre Glassdoor - {title} chez {company}",
            'Source': 'Glassdoor',
            'Télétravail': 'Non spécifié',
            'Compétences mentionnées': extract_skills_from_title(title),
            'Fourchette salariale': 'Non spécifié',
            'URL': "https://www.glassdoor.fr"
        }
    except Exception as e:
        print(f"   ⚠ Erreur parsing Glassdoor: {e}")
        return None

def scrape_chooseyourboss():
    """Scraping ChooseYourBoss - startups françaises"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8'
    }
    
    offers = []
    
    # URLs ChooseYourBoss
    cyb_urls = [
        "https://www.chooseyourboss.com/offres/stage?q=informatique",
        "https://www.chooseyourboss.com/offres/stage?q=d%C3%A9veloppement",
        "https://www.chooseyourboss.com/offres/alternance?q=informatique",
        "https://www.chooseyourboss.com/offres/alternance?q=d%C3%A9veloppement"
    ]
    
    for url in cyb_urls:
        try:
            contract_type = "Stage" if "stage" in url else "Alternance"
            print(f"   🔍 Recherche: {contract_type}")
            
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Sélecteurs ChooseYourBoss
                job_cards = soup.find_all('div', class_=['job-item', 'offer-card'])
                
                for card in job_cards[:10]:
                    offer = parse_chooseyourboss_card(card, contract_type)
                    if offer:
                        offers.append(offer)
                
            time.sleep(2)
            
        except Exception as e:
            print(f"   ❌ Erreur ChooseYourBoss: {e}")
    
    return offers

def parse_chooseyourboss_card(card, contract_type):
    """Parser une carte ChooseYourBoss"""
    try:
        # Titre
        title_elem = card.find(['h3', 'h2'], class_=['title', 'job-title'])
        title = title_elem.get_text(strip=True) if title_elem else f"{contract_type} Informatique"
        
        # Entreprise
        company_elem = card.find(['div', 'span'], class_=['company', 'employer'])
        company = company_elem.get_text(strip=True) if company_elem else "Startup Tech"
        
        # Localisation
        location_elem = card.find(['div', 'span'], class_=['location', 'city'])
        location = location_elem.get_text(strip=True) if location_elem else "France"
        
        # Salaire (parfois disponible sur ChooseYourBoss)
        salary_elem = card.find(['div', 'span'], class_=['salary', 'compensation'])
        salaire = salary_elem.get_text(strip=True) if salary_elem else "Non spécifié"
        
        return {
            'Intitulé du poste': title,
            'Nom de l entreprise': company,
            'Ville ou région': location,
            'Date de publication': datetime.now().strftime("%d/%m/%Y"),
            'Type de contrat': contract_type,
            'Nombre d années d expérience demandées': '0',
            'Niveau de seniorité': 'Étudiant',
            'Description du poste': f"Offre ChooseYourBoss - {title} chez {company}",
            'Source': 'ChooseYourBoss',
            'Télétravail': detect_teletravail_cyb(card),
            'Compétences mentionnées': extract_skills_from_title(title),
            'Fourchette salariale': salaire,
            'URL': "https://www.chooseyourboss.com" + card.find('a')['href'] if card.find('a') else "Non disponible"
        }
    except Exception as e:
        print(f"   ⚠ Erreur parsing ChooseYourBoss: {e}")
        return None

def detect_teletravail_cyb(card):
    """Détecter télétravail ChooseYourBoss"""
    card_text = str(card).lower()
    teletravail_keywords = ['remote', 'télétravail', 'hybride', 'flexible']
    return 'Oui' if any(keyword in card_text for keyword in teletravail_keywords) else 'Non'

def extract_skills_from_title(title):
    """Extraire les compétences depuis le titre"""
    title_lower = title.lower()
    skills = []
    
    competences_tech = [
        'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
        'sql', 'mongodb', 'docker', 'kubernetes', 'aws', 'azure', 'gcp',
        'machine learning', 'data science', 'devops', 'cloud', 'php',
        'symfony', 'laravel', 'c#', '.net', 'html', 'css', 'typescript'
    ]
    
    for skill in competences_tech:
        if skill in title_lower:
            skills.append(skill)
    
    return ', '.join(skills) if skills else 'Non spécifié'

def save_offers_csv(offers):
    """Sauvegarder les offres en CSV"""
    if not offers:
        print("❌ Aucune donnée à sauvegarder")
        return None
    
    os.makedirs('data/offres', exist_ok=True)
    
    df = pd.DataFrame(offers)
    
    # Réorganiser les colonnes
    column_order = [
        'Intitulé du poste',
        'Nom de l entreprise',
        'Ville ou région',
        'Date de publication',
        'Type de contrat',
        'Nombre d années d expérience demandées',
        'Niveau de seniorité',
        'Télétravail',
        'Fourchette salariale',
        'Compétences mentionnées',
        'Source',
        'URL',
        'Description du poste'
    ]
    
    existing_columns = [col for col in column_order if col in df.columns]
    df = df[existing_columns]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/offres/stages_alternance_{timestamp}.csv"
    df.to_csv(filename, index=False, encoding='utf-8')
    
    return filename

def create_demo_data():
    """Créer des données de démonstration si le scraping échoue"""
    print("📝 CRÉATION DE DONNÉES DE DÉMONSTRATION...")
    
    demo_offers = [
        {
            'Intitulé du poste': 'Stage Développeur FullStack React/Node.js',
            'Nom de l entreprise': 'Startup Tech Paris',
            'Ville ou région': 'Paris',
            'Date de publication': '15/01/2024',
            'Type de contrat': 'Stage',
            'Nombre d années d expérience demandées': '0',
            'Niveau de seniorité': 'Étudiant',
            'Description du poste': 'Stage en développement FullStack avec React et Node.js. Participation à des projets innovants.',
            'Source': 'Données Démo',
            'Télétravail': 'Hybride',
            'Compétences mentionnées': 'javascript, react, node.js, sql',
            'Fourchette salariale': 'Gratification légale',
            'URL': 'https://example.com/offre1'
        },
        {
            'Intitulé du poste': 'Alternance Data Analyst Python/SQL',
            'Nom de l entreprise': 'Data Company',
            'Ville ou région': 'Lyon',
            'Date de publication': '10/01/2024',
            'Type de contrat': 'Alternance',
            'Nombre d années d expérience demandées': '0',
            'Niveau de seniorité': 'Étudiant',
            'Description du poste': 'Alternance en analyse de données avec Python, SQL et outils de visualisation.',
            'Source': 'Données Démo',
            'Télétravail': 'Non',
            'Compétences mentionnées': 'python, sql, data analysis, pandas',
            'Fourchette salariale': 'Salaire alternance',
            'URL': 'https://example.com/offre2'
        },
        {
            'Intitulé du poste': 'Stage DevOps AWS/Docker',
            'Nom de l entreprise': 'Cloud Solutions',
            'Ville ou région': 'Toulouse',
            'Date de publication': '20/01/2024',
            'Type de contrat': 'Stage',
            'Nombre d années d expérience demandées': '0',
            'Niveau de seniorité': 'Étudiant',
            'Description du poste': 'Stage en infrastructure cloud et automatisation avec AWS et Docker.',
            'Source': 'Données Démo',
            'Télétravail': 'Oui',
            'Compétences mentionnées': 'aws, docker, python, linux',
            'Fourchette salariale': 'Gratification légale',
            'URL': 'https://example.com/offre3'
        },
        {
            'Intitulé du poste': 'Alternance Développeur Mobile Flutter',
            'Nom de l entreprise': 'App Startup',
            'Ville ou région': 'Bordeaux',
            'Date de publication': '12/01/2024',
            'Type de contrat': 'Alternance',
            'Nombre d années d expérience demandées': '0',
            'Niveau de seniorité': 'Étudiant',
            'Description du poste': 'Alternance en développement mobile cross-platform avec Flutter.',
            'Source': 'Données Démo',
            'Télétravail': 'Hybride',
            'Compétences mentionnées': 'flutter, dart, mobile, android, ios',
            'Fourchette salariale': 'Salaire alternance',
            'URL': 'https://example.com/offre4'
        }
    ]
    
    return demo_offers

def main():
    """Programme principal"""
    print("🚀 COLLECTE STAGES & ALTERNANCE 2024/2025")
    print("Sites accessibles: LinkedIn, Glassdoor, ChooseYourBoss")
    print("=" * 60)
    
    # Essayer le scraping réel
    offers = scrape_accessible_sites()
    
    # Si échec, utiliser les données de démonstration
    if not offers:
        print("\n⚠ Le scraping a échoué, utilisation de données de démonstration...")
        offers = create_demo_data()
    
    if offers:
        # Sauvegarde
        csv_file = save_offers_csv(offers)
        
        # Statistiques
        print(f"\n📊 RÉSULTATS:")
        print(f"🎯 Total offres collectées: {len(offers)}")
        
        df = pd.DataFrame(offers)
        
        print(f"🏢 Entreprises uniques: {df['Nom de l entreprise'].nunique()}")
        print(f"📍 Villes représentées: {df['Ville ou région'].nunique()}")
        
        # Répartition par source
        print(f"\n🔍 RÉPARTITION PAR SOURCE:")
        source_stats = df['Source'].value_counts()
        for source, count in source_stats.items():
            print(f"   - {source}: {count} offres")
        
        # Répartition par type
        print(f"\n📄 RÉPARTITION PAR TYPE DE CONTRAT:")
        contract_stats = df['Type de contrat'].value_counts()
        for contrat, count in contract_stats.items():
            print(f"   - {contrat}: {count} offres")
        
        print(f"\n💾 FICHIER SAUVEGARDÉ: {csv_file}")
        
        # Aperçu
        print(f"\n👀 APERÇU DES OFFRES:")
        preview_cols = ['Intitulé du poste', 'Nom de l entreprise', 'Type de contrat', 'Source']
        print(df[preview_cols].to_string(index=False))
        
        return csv_file
    else:
        print("❌ Aucune offre collectée")
        return None

if _name_ == "_main_":
    result_file = main()
    
    if result_file:
        print(f"\n✅ COLLECTE TERMINÉE!")
        print(f"📥 Fichier CSV: {result_file}")
        df_result = pd.read_csv(result_file)
        print(f"📊 {len(df_result)} offres sauvegardées")
    else:
        print("\n❌ Échec de la collecte")