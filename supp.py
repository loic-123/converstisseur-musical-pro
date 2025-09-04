import streamlit as st
import yt_dlp
import os
import tempfile
from pathlib import Path
import re
import subprocess
import io
import zipfile
import time
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

def check_ffmpeg():
    """Vérifie si FFmpeg est installé"""
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def clean_filename(filename):
    """Nettoie le nom de fichier pour éviter les caractères problématiques"""
    # Remplace les caractères non alphanumériques par des underscores
    cleaned = re.sub(r'[^\w\s-]', '', filename)
    cleaned = re.sub(r'[-\s]+', '_', cleaned)
    return cleaned[:50]  # Limite la longueur

def download_from_youtube(url, output_path, audio_format='mp3', quality='192'):
    """Télécharge l'audio depuis YouTube avec yt-dlp"""
    try:
        # Configuration de qualité selon le format
        if audio_format == 'mp3':
            codec_opts = {
                'preferredcodec': 'mp3',
                'preferredquality': quality,
            }
        elif audio_format == 'wav':
            codec_opts = {
                'preferredcodec': 'wav',
                'preferredquality': 'best',
            }
        elif audio_format == 'flac':
            codec_opts = {
                'preferredcodec': 'flac',
                'preferredquality': 'best',
            }
        elif audio_format == 'ogg':
            codec_opts = {
                'preferredcodec': 'vorbis',
                'preferredquality': quality,
            }
        else:
            codec_opts = {
                'preferredcodec': audio_format,
                'preferredquality': quality,
            }
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                **codec_opts,
            }],
            'postprocessor_args': [
                '-ar', '44100',  # Sample rate
                '-ac', '2',      # Stereo
            ],
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Récupère les infos de la vidéo
            info = ydl.extract_info(url, download=False)
            title = clean_filename(info.get('title', 'Unknown'))
            duration = info.get('duration', 0)
            
            # Télécharge
            ydl.download([url])
            
            # Trouve le fichier téléchargé
            for file in os.listdir(output_path):
                if file.endswith(f'.{audio_format}'):
                    return os.path.join(output_path, file), title, duration
            
    except Exception as e:
        raise Exception(f"Erreur lors du téléchargement: {str(e)}")

def convert_with_ffmpeg(input_file, output_path, output_format, quality=192):
    """Convertit un fichier audio avec FFmpeg directement"""
    try:
        # Génère le nom du fichier de sortie
        input_name = os.path.splitext(os.path.basename(input_file.name))[0]
        output_filename = f"{clean_filename(input_name)}.{output_format}"
        output_file = os.path.join(output_path, output_filename)
        
        # Sauvegarde le fichier uploadé temporairement
        temp_input = os.path.join(output_path, f"temp_{input_file.name}")
        with open(temp_input, 'wb') as f:
            f.write(input_file.read())
        
        # Commande FFmpeg selon le format
        if output_format == 'mp3':
            cmd = [
                'ffmpeg', '-i', temp_input,
                '-codec:a', 'libmp3lame',
                '-b:a', f'{quality}k',
                '-ar', '44100',
                '-ac', '2',
                '-y',  # Overwrite output files
                output_file
            ]
        elif output_format == 'wav':
            cmd = [
                'ffmpeg', '-i', temp_input,
                '-codec:a', 'pcm_s16le',
                '-ar', '44100',
                '-ac', '2',
                '-y',
                output_file
            ]
        elif output_format == 'flac':
            cmd = [
                'ffmpeg', '-i', temp_input,
                '-codec:a', 'flac',
                '-ar', '44100',
                '-ac', '2',
                '-y',
                output_file
            ]
        elif output_format == 'ogg':
            cmd = [
                'ffmpeg', '-i', temp_input,
                '-codec:a', 'libvorbis',
                '-b:a', f'{quality}k',
                '-ar', '44100',
                '-ac', '2',
                '-y',
                output_file
            ]
        
        # Exécute la conversion
        result = subprocess.run(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Nettoie le fichier temporaire
        os.remove(temp_input)
        
        if result.returncode != 0:
            raise Exception(f"Erreur FFmpeg: {result.stderr}")
        
        return output_file, output_filename
        
    except Exception as e:
        # Nettoie en cas d'erreur
        if os.path.exists(temp_input):
            os.remove(temp_input)
        raise Exception(f"Erreur lors de la conversion: {str(e)}")

def format_duration(seconds):
    """Formate la durée en minutes:secondes"""
    if seconds:
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes}:{seconds:02d}"
    return "N/A"

def main():
    st.markdown('<h1 class="main-header">🎵 Convertisseur Musical Pro</h1>', unsafe_allow_html=True)
    
    # Vérification de FFmpeg
    if not check_ffmpeg():
        st.markdown("""
        <div class="warning-box">
        <h4>⚠️ FFmpeg non trouvé</h4>
        <p>FFmpeg est requis pour le fonctionnement de cette application.</p>
        <p><strong>Installation :</strong></p>
        <ul>
        <li><strong>Windows:</strong> Téléchargez depuis <a href="https://ffmpeg.org/download.html" target="_blank" style="color: white;">ffmpeg.org</a></li>
        <li><strong>macOS:</strong> <code>brew install ffmpeg</code></li>
        <li><strong>Ubuntu/Debian:</strong> <code>sudo apt install ffmpeg</code></li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Sidebar pour la configuration
    with st.sidebar:
        st.markdown("### ⚙️ Configuration")
        
        # Sélection du mode
        mode = st.selectbox(
            "Mode d'utilisation",
            ["📥 Télécharger depuis YouTube", "🔄 Convertir fichier local"]
        )
        
        # Configuration qualité
        if mode == "📥 Télécharger depuis YouTube":
            quality = st.selectbox("Qualité audio", ["128", "192", "256", "320"], index=1)
            output_format = st.selectbox("Format de sortie", ["mp3", "wav", "ogg", "flac"], index=0)
        else:
            output_format = st.selectbox("Format de conversion", ["mp3", "wav", "ogg", "flac"], index=0)
            if output_format == "mp3":
                quality = st.selectbox("Qualité MP3", ["128", "192", "256", "320"], index=1)
            else:
                quality = "192"  # Valeur par défaut pour autres formats
        
        # Informations système
        st.markdown("### 📊 État du système")
        st.success("✅ FFmpeg détecté")
        st.info(f"🎯 Format: {output_format.upper()}")
        if output_format == "mp3":
            st.info(f"🔊 Qualité: {quality} kbps")
    
    # Interface principale selon le mode
    if mode == "📥 Télécharger depuis YouTube":
        st.markdown("""
        <div class="feature-box">
        <h3>📥 Téléchargement depuis YouTube</h3>
        <p>Téléchargez vos propres créations musicales depuis YouTube en haute qualité</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Zone de saisie pour l'URL
        col1, col2 = st.columns([3, 1])
        
        with col1:
            youtube_url = st.text_input(
                "URL YouTube de votre création",
                placeholder="https://www.youtube.com/watch?v=...",
                help="Collez ici l'URL de votre vidéo YouTube"
            )
        
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Espacement
            download_btn = st.button("🚀 Télécharger", type="primary")
        
        if download_btn and youtube_url:
            if not youtube_url.strip():
                st.error("❌ Veuillez entrer une URL YouTube valide")
            else:
                with st.spinner("🎵 Téléchargement en cours..."):
                    try:
                        # Crée un dossier temporaire
                        temp_dir = tempfile.mkdtemp()
                        
                        # Télécharge depuis YouTube
                        file_path, title, duration = download_from_youtube(
                            youtube_url, temp_dir, output_format, quality
                        )
                        
                        # Affiche les informations
                        st.markdown(f"""
                        <div class="success-box">
                        <h4>✅ Téléchargement réussi!</h4>
                        <p><strong>Titre:</strong> {title}</p>
                        <p><strong>Durée:</strong> {format_duration(duration)}</p>
                        <p><strong>Format:</strong> {output_format.upper()}</p>
                        <p><strong>Qualité:</strong> {quality} kbps</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Bouton de téléchargement
                        with open(file_path, 'rb') as file:
                            st.download_button(
                                label=f"💾 Télécharger {title}.{output_format}",
                                data=file.read(),
                                file_name=f"{title}.{output_format}",
                                mime=f"audio/{output_format}",
                                type="primary"
                            )
                        
                        # Nettoyage
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        
                    except Exception as e:
                        st.error(f"❌ Erreur: {str(e)}")
                        st.markdown("""
                        <div class="warning-box">
                        <h4>💡 Conseils de dépannage:</h4>
                        <ul>
                        <li>Vérifiez que l'URL est correcte et accessible</li>
                        <li>Assurez-vous que vous possédez les droits sur le contenu</li>
                        <li>Certaines vidéos peuvent être protégées contre le téléchargement</li>
                        <li>Vérifiez votre connexion internet</li>
                        </ul>
                        </div>
                        """, unsafe_allow_html=True)
    
    else:  # Mode conversion de fichier local
        st.markdown("""
        <div class="feature-box">
        <h3>🔄 Conversion de fichiers audio</h3>
        <p>Convertissez vos fichiers audio locaux vers différents formats</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Upload de fichier
        uploaded_files = st.file_uploader(
            "Sélectionnez vos fichiers audio",
            type=['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'],
            accept_multiple_files=True,
            help="Formats supportés: MP3, WAV, OGG, FLAC, M4A, AAC, WMA"
        )
        
        if uploaded_files:
            st.markdown(f"**{len(uploaded_files)} fichier(s) sélectionné(s)**")
            
            # Affichage des fichiers
            for i, file in enumerate(uploaded_files):
                st.write(f"📄 {file.name} ({file.size / 1024 / 1024:.1f} MB)")
            
            # Bouton de conversion
            if st.button("🔄 Convertir tous les fichiers", type="primary"):
                with st.spinner(f"🎵 Conversion vers {output_format.upper()} en cours..."):
                    try:
                        temp_dir = tempfile.mkdtemp()
                        converted_files = []
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        for i, uploaded_file in enumerate(uploaded_files):
                            # Met à jour la barre de progression
                            progress = (i + 1) / len(uploaded_files)
                            progress_bar.progress(progress)
                            status_text.text(f"Conversion de {uploaded_file.name}...")
                            
                            # Reset du pointeur de fichier
                            uploaded_file.seek(0)
                            
                            # Convertit le fichier
                            output_path, filename = convert_with_ffmpeg(
                                uploaded_file, temp_dir, output_format, quality
                            )
                            
                            # Lit le fichier converti
                            with open(output_path, 'rb') as f:
                                converted_data = f.read()
                            
                            converted_files.append((filename, converted_data))
                            
                            # Nettoie le fichier temporaire
                            os.remove(output_path)
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.markdown(f"""
                        <div class="success-box">
                        <h4>✅ Conversion terminée!</h4>
                        <p>{len(converted_files)} fichier(s) converti(s) vers {output_format.upper()}</p>
                        <p><strong>Qualité:</strong> {quality} kbps</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Si un seul fichier, bouton de téléchargement direct
                        if len(converted_files) == 1:
                            filename, data = converted_files[0]
                            st.download_button(
                                label=f"💾 Télécharger {filename}",
                                data=data,
                                file_name=filename,
                                mime=f"audio/{output_format}",
                                type="primary"
                            )
                        
                        # Si plusieurs fichiers, création d'un ZIP
                        else:
                            zip_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for filename, data in converted_files:
                                    zip_file.writestr(filename, data)
                            
                            st.download_button(
                                label=f"📦 Télécharger l'archive ZIP ({len(converted_files)} fichiers)",
                                data=zip_buffer.getvalue(),
                                file_name=f"converted_audio_{output_format}.zip",
                                mime="application/zip",
                                type="primary"
                            )
                        
                        # Nettoyage
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la conversion: {str(e)}")
                        st.markdown("""
                        <div class="info-box">
                        <h4>🔧 Vérifications:</h4>
                        <ul>
                        <li>Le fichier source est-il dans un format supporté ?</li>
                        <li>FFmpeg est-il correctement installé ?</li>
                        <li>Y a-t-il suffisamment d'espace disque ?</li>
                        </ul>
                        </div>
                        """, unsafe_allow_html=True)
    
    # Footer avec informations
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; margin-top: 30px;">
    <p>🎵 <strong>Convertisseur Musical Pro</strong> - Version sans PyAudio</p>
    <p><small>⚠️ Utilisez uniquement avec du contenu dont vous possédez les droits</small></p>
    <p><small>🔧 Utilise FFmpeg + yt-dlp pour une compatibilité maximale</small></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()