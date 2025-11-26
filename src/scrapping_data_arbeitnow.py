import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime
import time
from collections import Counter

def scrape_arbeitnow_france_it(max_results=50):
    """
    Scrape les offres IT en France depuis Arbeitnow
    """
    base_url = "https://www.arbeitnow.com"
    
    # Catégories IT sur Arbeitnow
    it_categories = [
        "developer", "engineering", "devops", "data", 
        "design", "product", "qa", "security", "systems-administrator"
    ]
    
    all_offres = []
    
    for category in it_categories:
        print(f"Recherche dans la catégorie: {category}")
        
        search_url = f"{base_url}/api/job-board?category={category}&location=france"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://www.arbeitnow.com/'
        }
        
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data:
                jobs = data['data']
                print(f"  Trouvé {len(jobs)} offres dans cette catégorie")
                
                for job in jobs:
                    if len(all_offres) >= max_results:
                        break
                        
                    try:
                        offre = process_job_data_france_it(job, base_url, category)
                        if offre and is_it_related(offre):
                            all_offres.append(offre)
                            print(f"  ✓ {offre['intitule_poste'][:40]}...")
                            
                    except Exception as e:
                        print(f"  Erreur traitement offre: {e}")
                        continue
            else:
                print(f"  Aucune donnée pour {category}")
                
            time.sleep(1)  # Respect rate limiting
            
        except Exception as e:
            print(f"Erreur pour la catégorie {category}: {e}")
        
        if len(all_offres) >= max_results:
            break
    
    return all_offres

def process_job_data_france_it(job, base_url, category):
    """
    Traite les données d'une offre IT en France
    """
    # Nettoyer et formater les données
    intitule_poste = job.get('title', '').strip()
    nom_entreprise = job.get('company_name', '').strip()
    location = job.get('location', '').strip()
    
    # Vérifier que c'est bien en France
    if not is_french_location(location):
        return None
    
    # Description
    description = job.get('description', '')
    
    # URL complète
    slug = job.get('slug', '')
    source_offre = f"{base_url}/jobs/{slug}" if slug else ""
    
    # Date de publication
    created_at = job.get('created_at')
    date_publication = parse_timestamp(created_at) if created_at else datetime.now().isoformat()
    
    # Type de contrat
    job_types = job.get('job_types', [])
    type_contrat = determine_contract_type_fr(job_types)
    
    # Télétravail
    remote = job.get('remote', False)
    teletravail = "Oui" if remote else "Non"
    
    # Tags pour les compétences
    tags = job.get('tags', [])
    
    # Niveau de séniorité et expérience
    experience_demandee, niveau_seniorite = determine_experience_and_seniority_it(intitule_poste, description, tags)
    
    # Compétences IT
    competences_mentionnees = extract_it_skills(description, tags, intitule_poste)
    
    # Métier IT spécifique
    metier_recherche = determine_it_job_type(intitule_poste, description, competences_mentionnees)
    
    # Fourchette salariale (non disponible sur Arbeitnow)
    fourchette_salaire = "Non spécifié"
    
    # ID de l'offre
    id_offre = slug or str(job.get('id', ''))
    
    # Construire l'objet final
    offre = {
        "intitule_poste": intitule_poste,
        "nom_entreprise": nom_entreprise,
        "ville_region": format_french_location(location),
        "date_publication": date_publication,
        "type_contrat": type_contrat,
        "experience_demandee": experience_demandee,
        "niveau_seniorite": niveau_seniorite,
        "description_poste": description,
        "source_offre": source_offre,
        "teletravail": teletravail,
        "competences_mentionnees": competences_mentionnees,
        "fourchette_salaire": fourchette_salaire,
        "metier_recherche": metier_recherche,
        "id_offre": id_offre
    }
    
    return offre

def is_french_location(location):
    """
    Vérifie si la localisation est en France
    """
    french_indicators = [
        'france', 'paris', 'lyon', 'marseille', 'toulouse', 'nice', 'nantes',
        'strasbourg', 'montpellier', 'bordeaux', 'lille', 'rennes', 'reims',
        'saint-étienne', 'toulon', 'grenoble', 'dijon', 'angers', 'villeurbanne',
        'le havre', 'saint-denis', 'rouen', 'avignon', 'nanterre', 'créteil'
    ]
    
    location_lower = location.lower()
    return any(indicator in location_lower for indicator in french_indicators)

def format_french_location(location):
    """
    Formate la localisation française
    """
    # Simplifier la localisation
    if 'paris' in location.lower():
        return "Paris"
    elif 'lyon' in location.lower():
        return "Lyon"
    elif 'marseille' in location.lower():
        return "Marseille"
    elif 'toulouse' in location.lower():
        return "Toulouse"
    elif 'remote' in location.lower() or 'télétravail' in location.lower():
        return "Remote France"
    else:
        return location

def determine_contract_type_fr(job_types):
    """
    Détermine le type de contrat en français
    """
    if not job_types:
        return "Non spécifié"
    
    type_mapping = {
        'full_time': 'CDI',
        'part_time': 'Temps partiel',
        'contract': 'CDD',
        'internship': 'Stage',
        'freelance': 'Freelance',
        'temporary': 'Intérim'
    }
    
    french_types = []
    for job_type in job_types:
        if job_type in type_mapping:
            french_types.append(type_mapping[job_type])
        else:
            french_types.append(job_type)
    
    return " | ".join(french_types) if french_types else "CDI"

def determine_experience_and_seniority_it(title, description, tags):
    """
    Détermine l'expérience demandée et le niveau de séniorité pour les métiers IT
    """
    full_text = (title + " " + description).lower()
    
    # Niveau de séniorité
    if any(word in full_text for word in ['senior', 'sr.', 'experimenté', '5+ years', '5 ans', '7 ans', '10 ans']):
        niveau_seniorite = "Senior"
        experience_demandee = "5+ ans"
    elif any(word in full_text for word in ['mid-level', 'mid level', 'confirmé', '3 ans', '4 ans', '3+ years', '4+ years']):
        niveau_seniorite = "Confirmé"
        experience_demandee = "3-4 ans"
    elif any(word in full_text for word in ['junior', 'débutant', 'entry level', '0-2 years', '1 an', '2 ans', 'graduate']):
        niveau_seniorite = "Junior"
        experience_demandee = "0-2 ans"
    elif any(word in full_text for word in ['intern', 'stage', 'stagiaire', 'apprenti']):
        niveau_seniorite = "Débutant"
        experience_demandee = "Stage"
    else:
        niveau_seniorite = "Non spécifié"
        experience_demandee = "Non spécifié"
    
    return experience_demandee, niveau_seniorite

def extract_it_skills(description, tags, title):
    """
    Extrait les compétences IT spécifiques
    """
    skills = set()
    full_text = (title + " " + description).lower()
    
    # Mapping des compétences IT
    it_skills_mapping = {
        # Langages de programmation
        'python': 'python', 'java': 'java', 'javascript': 'javascript', 
        'typescript': 'typescript', 'c++': 'c++', 'c#': 'c#', 'php': 'php',
        'ruby': 'ruby', 'go': 'go', 'rust': 'rust', 'kotlin': 'kotlin',
        'swift': 'swift', 'dart': 'dart', 'scala': 'scala',
        
        # Frameworks et bibliothèques
        'react': 'react', 'angular': 'angular', 'vue': 'vue', 'vue.js': 'vue',
        'node.js': 'node.js', 'node': 'node.js', 'express': 'express',
        'django': 'django', 'flask': 'flask', 'spring': 'spring', 'laravel': 'laravel',
        'symfony': 'symfony', 'rails': 'rails', 'asp.net': 'asp.net',
        
        # Bases de données
        'sql': 'sql', 'mysql': 'mysql', 'postgresql': 'postgresql', 
        'mongodb': 'mongodb', 'redis': 'redis', 'elasticsearch': 'elasticsearch',
        'oracle': 'oracle', 'sql server': 'sql server',
        
        # Cloud et DevOps
        'docker': 'docker', 'kubernetes': 'kubernetes', 'aws': 'aws',
        'azure': 'azure', 'gcp': 'gcp', 'terraform': 'terraform',
        'ansible': 'ansible', 'jenkins': 'jenkins', 'gitlab': 'gitlab',
        'github actions': 'github actions',
        
        # Outils et méthodes
        'git': 'git', 'linux': 'linux', 'rest api': 'rest api', 'graphql': 'graphql',
        'agile': 'agile', 'scrum': 'scrum', 'devops': 'devops',
        
        # Spécialités
        'machine learning': 'machine learning', 'ai': 'ai', 
        'data science': 'data science', 'big data': 'big data',
        'cybersecurity': 'cybersecurity', 'blockchain': 'blockchain',
        'iot': 'iot', 'embedded': 'embedded'
    }
    
    # Vérifier les tags
    for tag in tags:
        tag_lower = tag.lower()
        if tag_lower in it_skills_mapping:
            skills.add(it_skills_mapping[tag_lower])
    
    # Vérifier dans le texte
    for skill_key, skill_value in it_skills_mapping.items():
        if skill_key in full_text:
            skills.add(skill_value)
    
    # Recherche par patterns pour les compétences communes
    patterns = {
        r'react\.?js': 'react',
        r'node\.?js': 'node.js',
        r'vue\.?js': 'vue',
        r'postgres': 'postgresql',
        r'mongo': 'mongodb',
        r'kubernetes': 'kubernetes',
        r'docker': 'docker',
        r'aws': 'aws',
        r'azure': 'azure',
        r'google cloud': 'gcp',
        r'machine learning': 'machine learning',
        r'data science': 'data science'
    }
    
    for pattern, skill in patterns.items():
        if re.search(pattern, full_text):
            skills.add(skill)
    
    return list(skills)

def determine_it_job_type(title, description, skills):
    """
    Détermine le type de métier IT
    """
    full_text = (title + " " + description).lower()
    
    job_patterns = {
        'développeur': ['developer', 'développeur', 'dev', 'software engineer', 'ingénieur logiciel'],
        'frontend': ['frontend', 'front-end', 'react', 'angular', 'vue', 'javascript'],
        'backend': ['backend', 'back-end', 'server', 'api', 'database'],
        'fullstack': ['fullstack', 'full-stack'],
        'data': ['data scientist', 'data engineer', 'data analyst', 'machine learning', 'ai'],
        'devops': ['devops', 'sre', 'site reliability', 'infrastructure'],
        'mobile': ['mobile', 'ios', 'android', 'react native', 'flutter'],
        'qa': ['qa', 'quality assurance', 'test', 'testing'],
        'security': ['security', 'cybersecurity', 'sécurité']
    }
    
    for job_type, keywords in job_patterns.items():
        if any(keyword in full_text for keyword in keywords):
            return job_type
    
    # Déduire des compétences
    if 'react' in skills or 'angular' in skills or 'vue' in skills:
        return 'frontend'
    elif 'node.js' in skills or 'spring' in skills or 'django' in skills:
        return 'backend'
    elif 'python' in skills and ('machine learning' in skills or 'data science' in skills):
        return 'data'
    elif 'docker' in skills or 'kubernetes' in skills or 'aws' in skills:
        return 'devops'
    
    return 'développeur'

def is_it_related(offre):
    """
    Vérifie si l'offre est bien dans le domaine IT
    """
    it_keywords = [
        'developer', 'développeur', 'software', 'ingénieur', 'engineer',
        'programming', 'programmation', 'code', 'coding',
        'java', 'python', 'javascript', 'c++', 'php', 'ruby',
        'react', 'angular', 'vue', 'node', 'database', 'sql',
        'aws', 'azure', 'cloud', 'devops', 'frontend', 'backend',
        'fullstack', 'mobile', 'ios', 'android', 'qa', 'test',
        'data', 'ai', 'machine learning', 'cybersecurity'
    ]
    
    full_text = (offre['intitule_poste'] + " " + offre['description_poste']).lower()
    return any(keyword in full_text for keyword in it_keywords)

def parse_timestamp(timestamp):
    """
    Convertit un timestamp en date ISO
    """
    try:
        if timestamp:
            if isinstance(timestamp, (int, float)) and timestamp > 1000000000:
                return datetime.fromtimestamp(timestamp).isoformat()
            elif isinstance(timestamp, str):
                return timestamp
    except:
        pass
    return datetime.now().isoformat()

def generate_statistics(offres):
    """
    Génère des statistiques sur les offres récupérées
    """
    stats = {
        'total_offres': len(offres),
        'metiers': Counter(),
        'competences': Counter(),
        'villes': Counter(),
        'niveaux': Counter(),
        'teletravail': 0,
        'types_contrat': Counter()
    }
    
    for offre in offres:
        stats['metiers'][offre['metier_recherche']] += 1
        stats['niveaux'][offre['niveau_seniorite']] += 1
        stats['types_contrat'][offre['type_contrat']] += 1
        stats['villes'][offre['ville_region']] += 1
        
        if offre['teletravail'] == 'Oui':
            stats['teletravail'] += 1
            
        for competence in offre['competences_mentionnees']:
            stats['competences'][competence] += 1
    
    return stats

def main():
    """
    Fonction principale
    """
    print("🚀 Début du scraping des offres IT en France depuis Arbeitnow...")
    print("=" * 60)
    
    # Récupérer les offres
    offres = scrape_arbeitnow_france_it(max_results=30)
    
    if not offres:
        print("Aucune offre trouvée.")
        return
    
    # Sauvegarder les résultats
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f'offres_it_france_{timestamp}.json'
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(offres, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Scraping terminé. {len(offres)} offres IT françaises sauvegardées dans '{filename}'")
    
    # Générer les statistiques
    stats = generate_statistics(offres)
    
    print(f"\n📊 STATISTIQUES DÉTAILLÉES")
    print("=" * 40)
    
    print(f"\n🏢 RÉPARTITION PAR MÉTIER IT:")
    for metier, count in stats['metiers'].most_common():
        print(f"  {metier}: {count} offres ({count/len(offres)*100:.1f}%)")
    
    print(f"\n🎯 NIVEAUX DE SÉNIORITÉ:")
    for niveau, count in stats['niveaux'].most_common():
        print(f"  {niveau}: {count} offres")
    
    print(f"\n💻 TOP 15 COMPÉTENCES TECHNIQUES:")
    for competence, count in stats['competences'].most_common(15):
        print(f"  {competence}: {count} offres")
    
    print(f"\n📍 LOCALISATIONS:")
    for ville, count in stats['villes'].most_common(10):
        print(f"  {ville}: {count} offres")
    
    print(f"\n📝 TYPES DE CONTRAT:")
    for contrat, count in stats['types_contrat'].most_common():
        print(f"  {contrat}: {count} offres")
    
    print(f"\n🏠 TÉLÉTRAVAIL: {stats['teletravail']}/{len(offres)} offres ({stats['teletravail']/len(offres)*100:.1f}%)")
    
    # Afficher un exemple d'offre
    print(f"\n📄 EXEMPLE D'OFFRE RÉCUPÉRÉE:")
    print("=" * 40)
    if offres:
        exemple = offres[0]
        print(f"Poste: {exemple['intitule_poste']}")
        print(f"Entreprise: {exemple['nom_entreprise']}")
        print(f"Localisation: {exemple['ville_region']}")
        print(f"Métier: {exemple['metier_recherche']}")
        print(f"Niveau: {exemple['niveau_seniorite']}")
        print(f"Compétences: {', '.join(exemple['competences_mentionnees'][:10])}")
        print(f"Télétravail: {exemple['teletravail']}")

if __name__ == "__main__":
    main()