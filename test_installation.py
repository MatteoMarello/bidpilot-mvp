#!/usr/bin/env python3
"""
Script di test per verificare l'installazione di BidPilot MVP
Esegui con: python test_installation.py
"""
import sys
import os

def test_imports():
    """Test import di tutti i moduli necessari"""
    print("🧪 Testing imports...\n")
    
    tests = [
        ("Streamlit", "streamlit"),
        ("LangChain", "langchain"),
        ("LangChain OpenAI", "langchain_openai"),
        ("LangChain Community", "langchain_community"),
        ("ChromaDB", "chromadb"),
        ("PyPDF", "pypdf"),
        ("OpenAI", "openai"),
        ("Pydantic", "pydantic"),
    ]
    
    failed = []
    
    for name, module in tests:
        try:
            __import__(module)
            print(f"✅ {name}: OK")
        except ImportError as e:
            print(f"❌ {name}: FAILED - {str(e)}")
            failed.append(name)
    
    print()
    
    if failed:
        print(f"❌ {len(failed)} moduli mancanti. Esegui: pip install -r requirements.txt")
        return False
    else:
        print("✅ Tutti i moduli installati correttamente!")
        return True

def test_project_structure():
    """Test struttura directory del progetto"""
    print("\n🧪 Testing project structure...\n")
    
    required_dirs = [
        "config",
        "src",
        "data/progetti_storici",
    ]
    
    required_files = [
        "config/profilo_azienda.json",
        "src/parser.py",
        "src/analyzer.py",
        "src/rag_engine.py",
        "src/prompts.py",
        "app.py",
        "requirements.txt",
    ]
    
    missing_dirs = []
    missing_files = []
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"❌ Directory mancante: {dir_path}")
            missing_dirs.append(dir_path)
        else:
            print(f"✅ Directory: {dir_path}")
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ File mancante: {file_path}")
            missing_files.append(file_path)
        else:
            print(f"✅ File: {file_path}")
    
    print()
    
    if missing_dirs or missing_files:
        print(f"❌ Struttura incompleta: {len(missing_dirs)} dir, {len(missing_files)} file mancanti")
        return False
    else:
        print("✅ Struttura progetto completa!")
        return True

def test_profilo_aziendale():
    """Test caricamento profilo aziendale"""
    print("\n🧪 Testing profilo aziendale...\n")
    
    try:
        import json
        with open("config/profilo_azienda.json", 'r', encoding='utf-8') as f:
            profilo = json.load(f)
        
        required_keys = ["nome_azienda", "soa_possedute", "certificazioni", "fatturato"]
        
        for key in required_keys:
            if key in profilo:
                print(f"✅ Campo '{key}': presente")
            else:
                print(f"❌ Campo '{key}': mancante")
                return False
        
        print(f"\n✅ Profilo aziendale valido per: {profilo['nome_azienda']}")
        print(f"   - SOA: {len(profilo.get('soa_possedute', []))}")
        print(f"   - Certificazioni: {len(profilo.get('certificazioni', []))}")
        return True
        
    except Exception as e:
        print(f"❌ Errore nel caricamento profilo: {str(e)}")
        return False

def test_progetti_storici():
    """Test presenza progetti storici"""
    print("\n🧪 Testing progetti storici...\n")
    
    progetti_dir = "data/progetti_storici"
    
    if not os.path.exists(progetti_dir):
        print(f"⚠️  Directory {progetti_dir} non trovata")
        return False
    
    pdf_files = [f for f in os.listdir(progetti_dir) if f.endswith('.pdf')]
    
    if not pdf_files:
        print(f"⚠️  Nessun PDF trovato in {progetti_dir}")
        print("   Questo è OK per test iniziali, ma serve per generazione bozze.")
        print("   Aggiungi PDF in questa cartella e riindicizza dalla app.")
        return True
    else:
        print(f"✅ Trovati {len(pdf_files)} PDF in {progetti_dir}:")
        for pdf in pdf_files[:5]:  # Mostra max 5
            print(f"   - {pdf}")
        if len(pdf_files) > 5:
            print(f"   ... e altri {len(pdf_files) - 5}")
        return True

def main():
    """Esegui tutti i test"""
    print("=" * 60)
    print("🚀 BidPilot MVP - Installation Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Project Structure", test_project_structure()))
    results.append(("Profilo Aziendale", test_profilo_aziendale()))
    results.append(("Progetti Storici", test_progetti_storici()))
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results[:3])  # Progetti storici opzionale
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 Installazione completata con successo!")
        print("\nProssimi passi:")
        print("1. Esegui: streamlit run app.py")
        print("2. Inserisci OpenAI API Key nella sidebar")
        print("3. (Opzionale) Aggiungi PDF in data/progetti_storici/")
        print("4. Carica un bando e inizia ad analizzare!")
    else:
        print("❌ Alcuni test hanno fallito. Controlla gli errori sopra.")
        print("\nPer risolvere:")
        print("1. pip install -r requirements.txt")
        print("2. Verifica che tutti i file siano presenti")
    print("=" * 60)

if __name__ == "__main__":
    main()
