import streamlit as st
import yt_dlp
import os
import tempfile
import re
import shutil

st.set_page_config(
    page_title="YouTube Audio Downloader",
    page_icon="🎵",
    layout="wide"
)

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #FF6B6B;
        font-size: 2.5em;
        margin-bottom: 30px;
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
</style>
""", unsafe_allow_html=True)

def clean_filename(filename):
    """Nettoie le nom de fichier"""
    cleaned = re.sub(r'[^\w\s-]', '', filename)
    cleaned = re.sub(r'[-\s]+', '_', cleaned)
    return cleaned[:50]

def download_audio_direct(url, quality='192'):
    """Télécharge directement l'audio sans conversion FFmpeg"""
    try:
        temp_dir = tempfile.mkdtemp()
        
        # Configuration pour télécharger le meilleur audio disponible
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'no_warnings': True,
            'extractaudio': False,  # Pas de conversion
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Récupère les infos
            info = ydl.extract_info(url, download=False)
            title = clean_filename(info.get('title', 'Unknown'))
            duration = info.get('duration', 0)
            
            # Télécharge
            ydl.download([url])
            
            # Trouve le fichier téléchargé
            for file in os.listdir(temp_dir):
                if file.endswith(('.m4a', '.webm', '.opus', '.mp4')):
                    file_path = os.path.join(temp_dir, file)
                    
                    # Détermine l'extension finale
                    if file.endswith('.m4a'):
                        final_ext = 'm4a'
                    elif file.endswith('.webm'):
                        final_ext = 'webm'
                    else:
                        final_ext = 'mp4'
                    
                    return file_path, title, duration, final_ext
        
        raise Exception("Aucun fichier audio trouvé")
        
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
    st.markdown('<h1 class="main-header">🎵 YouTube Audio Downloader</h1>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="feature-box">
    <h3>📥 Téléchargement Audio depuis YouTube</h3>
    <p>Version simplifiée sans FFmpeg - Télécharge directement l'audio dans le format disponible</p>
    <p><strong>Formats supportés :</strong> M4A, WebM, MP4 (selon la disponibilité)</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Configuration
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        quality = st.selectbox("Qualité préférée", ["96", "128", "192", "256"], index=2)
        st.markdown("### 📊 État")
        st.success("✅ Aucune dépendance externe")
        st.info("🎯 Download direct")
        st.info(f"🔊 Qualité: Meilleure disponible")
    
    # Interface principale
    col1, col2 = st.columns([3, 1])
    
    with col1:
        youtube_url = st.text_input(
            "URL YouTube de votre création",
            placeholder="https://www.youtube.com/watch?v=...",
            help="Collez ici l'URL de votre vidéo YouTube"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        download_btn = st.button("🚀 Télécharger", type="primary")
    
    if download_btn and youtube_url:
        if not youtube_url.strip():
            st.error("❌ Veuillez entrer une URL YouTube valide")
        else:
            with st.spinner("🎵 Téléchargement en cours..."):
                try:
                    file_path, title, duration, file_ext = download_audio_direct(youtube_url, quality)
                    
                    # Détermine le type MIME
                    mime_types = {
                        'm4a': 'audio/mp4',
                        'webm': 'audio/webm', 
                        'mp4': 'video/mp4'
                    }
                    mime_type = mime_types.get(file_ext, 'audio/mpeg')
                    
                    st.markdown(f"""
                    <div class="success-box">
                    <h4>✅ Téléchargement réussi!</h4>
                    <p><strong>Titre:</strong> {title}</p>
                    <p><strong>Durée:</strong> {format_duration(duration)}</p>
                    <p><strong>Format:</strong> {file_ext.upper()}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Bouton de téléchargement
                    with open(file_path, 'rb') as file:
                        st.download_button(
                            label=f"💾 Télécharger {title}.{file_ext}",
                            data=file.read(),
                            file_name=f"{title}.{file_ext}",
                            mime=mime_type,
                            type="primary"
                        )
                    
                    # Nettoie le fichier temporaire
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")
    
    # Informations
    st.markdown("---")
    st.markdown("""
    ### 📋 Informations importantes
    
    - **Format de sortie :** Dépend de la source YouTube (généralement M4A ou WebM)
    - **Qualité :** Meilleure qualité disponible automatiquement sélectionnée
    - **Compatibilité :** Fonctionne sur tous les navigateurs modernes
    - **Légalité :** Utilisez uniquement avec du contenu dont vous possédez les droits
    
    ### 🔧 Pour la conversion de format
    
    Si vous avez besoin de convertir vers MP3 ou d'autres formats :
    1. Téléchargez le fichier avec cette application
    2. Utilisez un convertisseur en ligne comme [CloudConvert](https://cloudconvert.com)
    3. Ou installez un logiciel local comme Audacity
    """)
    
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 30px;">
    <p>🎵 <strong>YouTube Audio Downloader</strong> - Version Cloud-Friendly</p>
    <p><small>✨ Sans dépendances externes - Fonctionne partout</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()