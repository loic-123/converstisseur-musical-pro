import streamlit as st
import yt_dlp
import os
import tempfile
from pathlib import Path
import re
import subprocess
import io
import zipfile
import shutil

# Configuration de la page
st.set_page_config(
    page_title="Convertisseur Musical Pro",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #FF6B6B;
        font-size: 2.5em;
        margin-bottom: 30px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    .feature-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin: 10px 0;
    }
    .success-box {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .warning-box {
        background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
    .info-box {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def install_ffmpeg_cloud():
    """Installe FFmpeg sur Streamlit Cloud"""
    import platform
    import urllib.request
    import tarfile
    
    # Test si FFmpeg est déjà disponible
    ffmpeg_local = os.path.join(os.path.expanduser("~"), "ffmpeg")
    if os.path.exists(ffmpeg_local):
        try:
            subprocess.run([ffmpeg_local, '-version'], 
                          stdout=subprocess.DEVNULL, 
                          stderr=subprocess.DEVNULL, 
                          check=True, timeout=10)
            return ffmpeg_local, "FFmpeg local installé"
        except:
            pass
    
    # Test FFmpeg système
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True, timeout=10)
        return 'ffmpeg', "FFmpeg système détecté"
    except:
        pass
    
    # Installation FFmpeg statique sur Linux (Streamlit Cloud)
    if platform.system() == "Linux" and platform.machine() == "x86_64":
        try:
            st.info("Installation de FFmpeg en cours... (peut prendre 1-2 minutes)")
            
            # URL du binaire FFmpeg statique
            ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            home_dir = os.path.expanduser("~")
            
            # Télécharger FFmpeg
            with st.spinner("Téléchargement de FFmpeg..."):
                urllib.request.urlretrieve(ffmpeg_url, f"{home_dir}/ffmpeg.tar.xz")
            
            # Extraire
            with st.spinner("Extraction de FFmpeg..."):
                with tarfile.open(f"{home_dir}/ffmpeg.tar.xz", 'r:xz') as tar:
                    # Trouver le dossier extrait
                    members = tar.getnames()
                    ffmpeg_dir = members[0].split('/')[0]
                    tar.extractall(home_dir)
                
                # Copier l'exécutable
                extracted_ffmpeg = os.path.join(home_dir, ffmpeg_dir, "ffmpeg")
                if os.path.exists(extracted_ffmpeg):
                    shutil.copy2(extracted_ffmpeg, ffmpeg_local)
                    os.chmod(ffmpeg_local, 0o755)
                    
                    # Nettoyer
                    os.remove(f"{home_dir}/ffmpeg.tar.xz")
                    shutil.rmtree(os.path.join(home_dir, ffmpeg_dir))
                    
                    return ffmpeg_local, "FFmpeg installé avec succès"
        
        except Exception as e:
            st.error(f"Erreur d'installation FFmpeg: {str(e)}")
    
    return None, "FFmpeg non disponible"

def check_ffmpeg():
    """Vérifie la disponibilité de FFmpeg"""
    ffmpeg_path, status = install_ffmpeg_cloud()
    return ffmpeg_path is not None, ffmpeg_path, status

def clean_filename(filename):
    """Nettoie le nom de fichier"""
    cleaned = re.sub(r'[^\w\s-]', '', filename)
    cleaned = re.sub(r'[-\s]+', '_', cleaned)
    return cleaned[:50]

def download_from_youtube(url, output_path, audio_format='mp3', quality='192', ffmpeg_path='ffmpeg'):
    """Télécharge l'audio depuis YouTube"""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': quality,
            }],
            'postprocessor_args': ['-ar', '44100', '-ac', '2'],
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'no_warnings': True,
        }
        
        # Si FFmpeg n'est pas dans PATH, spécifier le chemin
        if ffmpeg_path != 'ffmpeg' and os.path.exists(ffmpeg_path):
            ydl_opts['ffmpeg_location'] = os.path.dirname(ffmpeg_path)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = clean_filename(info.get('title', 'Unknown'))
            duration = info.get('duration', 0)
            
            ydl.download([url])
            
            for file in os.listdir(output_path):
                if file.endswith(f'.{audio_format}'):
                    return os.path.join(output_path, file), title, duration
            
    except Exception as e:
        raise Exception(f"Erreur lors du téléchargement: {str(e)}")

def format_duration(seconds):
    """Formate la durée"""
    if seconds:
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    return "N/A"

def main():
    st.markdown('<h1 class="main-header">🎵 Convertisseur Musical Pro</h1>', unsafe_allow_html=True)
    
    # Vérification de FFmpeg
    ffmpeg_available, ffmpeg_path, ffmpeg_status = check_ffmpeg()
    
    if not ffmpeg_available:
        # Message spécifique pour Streamlit Cloud
        st.markdown("""
        <div class="warning-box">
        <h4>⚠️ Configuration requise pour Streamlit Cloud</h4>
        <p>Cette application nécessite FFmpeg. Pour le déploiement sur Streamlit Cloud :</p>
        <ol>
        <li>Créez un fichier <strong>packages.txt</strong> à la racine de votre projet</li>
        <li>Ajoutez cette ligne dans le fichier : <code>ffmpeg</code></li>
        <li>Commitez et pushez sur GitHub</li>
        <li>Redéployez l'application</li>
        </ol>
        <p><strong>Structure du projet :</strong></p>
        <pre>
votre-projet/
├── app.py
├── requirements.txt
├── packages.txt     ← AJOUTER CE FICHIER
└── README.md
        </pre>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-box">
        <h4>📝 Contenu de packages.txt</h4>
        <p>Créez un fichier texte nommé exactement <strong>packages.txt</strong> avec ce contenu :</p>
        <pre>ffmpeg</pre>
        <p>Cela installera automatiquement FFmpeg lors du déploiement sur Streamlit Cloud.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Version démo sans FFmpeg
        st.markdown("""
        <div class="feature-box">
        <h3>🎯 Mode Démo</h3>
        <p>En attendant la configuration FFmpeg, voici l'interface de l'application :</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Interface démo
        with st.sidebar:
            st.markdown("### ⚙️ Configuration")
            mode = st.selectbox("Mode d'utilisation", ["📥 Télécharger depuis YouTube", "🔄 Convertir fichier local"])
            quality = st.selectbox("Qualité audio", ["128", "192", "256", "320"], index=1)
            output_format = st.selectbox("Format de sortie", ["mp3", "wav", "ogg", "flac"], index=0)
            
            st.markdown("### 📊 État")
            st.error("❌ FFmpeg manquant")
            st.info("🛠️ Configuration requise")
        
        # Interface principale démo
        if mode == "📥 Télécharger depuis YouTube":
            col1, col2 = st.columns([3, 1])
            with col1:
                youtube_url = st.text_input("URL YouTube", placeholder="https://www.youtube.com/watch?v=...")
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 Télécharger", type="primary"):
                    st.error("Configuration FFmpeg requise pour cette fonctionnalité")
        else:
            uploaded_files = st.file_uploader("Sélectionnez vos fichiers audio", type=['mp3', 'wav', 'ogg'], accept_multiple_files=True)
            if uploaded_files and st.button("🔄 Convertir", type="primary"):
                st.error("Configuration FFmpeg requise pour cette fonctionnalité")
        
        return
    
    # Interface normale si FFmpeg disponible
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        mode = st.selectbox("Mode d'utilisation", ["📥 Télécharger depuis YouTube", "🔄 Convertir fichier local"])
        quality = st.selectbox("Qualité audio", ["128", "192", "256", "320"], index=1)
        output_format = st.selectbox("Format de sortie", ["mp3", "wav", "ogg", "flac"], index=0)
        
        st.markdown("### 📊 État")
        st.success("✅ FFmpeg prêt")
        st.info(f"📍 {ffmpeg_status}")
        st.info(f"🎯 Format: {output_format.upper()}")
        st.info(f"🔊 Qualité: {quality} kbps")
    
    if mode == "📥 Télécharger depuis YouTube":
        st.markdown("""
        <div class="feature-box">
        <h3>📥 Téléchargement depuis YouTube</h3>
        <p>Téléchargez vos propres créations musicales depuis YouTube</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            youtube_url = st.text_input("URL YouTube de votre création", placeholder="https://www.youtube.com/watch?v=...")
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            download_btn = st.button("🚀 Télécharger", type="primary")
        
        if download_btn and youtube_url:
            with st.spinner("🎵 Téléchargement en cours..."):
                try:
                    temp_dir = tempfile.mkdtemp()
                    
                    file_path, title, duration = download_from_youtube(
                        youtube_url, temp_dir, output_format, quality, ffmpeg_path
                    )
                    
                    st.markdown(f"""
                    <div class="success-box">
                    <h4>✅ Téléchargement réussi!</h4>
                    <p><strong>Titre:</strong> {title}</p>
                    <p><strong>Durée:</strong> {format_duration(duration)}</p>
                    <p><strong>Format:</strong> {output_format.upper()} - {quality} kbps</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with open(file_path, 'rb') as file:
                        st.download_button(
                            label=f"💾 Télécharger {title}.{output_format}",
                            data=file.read(),
                            file_name=f"{title}.{output_format}",
                            mime=f"audio/{output_format}",
                            type="primary"
                        )
                    
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666;">
    <p>🎵 <strong>Convertisseur Musical Pro</strong> - Version Cloud-Friendly</p>
    <p><small>✨ Optimisé pour Streamlit Cloud</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()