# Étape 1 : image de base légère
FROM python:3.11-slim

# Étape 2 : répertoire de travail
WORKDIR /app

# Étape 3 : copier requirements et installer les dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Étape 4 : copier uniquement les fichiers nécessaires
COPY main.py .
COPY src/ src/

# Étape 5 : exposer le port utilisé par Streamlit
EXPOSE 8501

# Étape 6 : commande de démarrage
CMD ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

