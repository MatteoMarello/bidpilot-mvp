#!/usr/bin/env python3
"""Script test installazione BidPilot MVP"""
import sys
import os


def test_imports():
    """Test import moduli"""
    print("🧪 Testing imports...\n")
    
    modules = [
        ("Streamlit", "streamlit"),
        ("LangChain", "langchain"),
        ("LangChain OpenAI", "langchain_openai"),
        ("ChromaDB", "chromadb"),
        ("PDF Processing", "pdfplumber"),
        ("OpenAI", "openai"),
        ("Pydantic", "pydantic"),
    ]
    
    failed = []
    
    for name, module in modules:
        try:
            __import__(module)
            print(f"✅ {name}")
        except ImportError as e:
            print(f"❌ {name}: {e}")
            failed.append(name)
    
    print()
    
    if failed:
        print(f"❌ {len(failed)} moduli mancanti. Eseguire: pip install -r requirements.txt")
        return False
    
    print("✅ Tutti i moduli installati!")
    return True


def test_structure():
    """Test struttura progetto"""
    print("🧪 Testing structure...\n")
    
    required = [
        "config/profilo_azienda.json",
        "src/parser.py",
        "src/analyzer.py",
        "src/schemas.py",
        "src/prompts.py",
        "app.py",
        "requirements.txt",
    ]
    
    missing = []
    
    for path in required:
        if os.path.exists(path):
            print(f"✅ {path}")
        else:
            print(f"❌ {path}")
            missing.append(path)
    
    print()
    
    if missing:
        print(f"❌ {len(missing)} file mancanti")
        return False
    
    print("✅ Struttura completa!")
    return True


def test_profilo():
    """Test profilo aziendale"""
    print("🧪 Testing profilo...\n")
    
    try:
        import json
        with open("config/profilo_azienda.json") as f:
            prof = json.load(f)
        
        for key in ["nome_azienda", "soa_possedute", "certificazioni"]:
            if key in prof:
                print(f"✅ Campo '{key}'")
            else:
                print(f"❌ Campo '{key}' mancante")
                return False
        
        print(f"\n✅ Profilo valido: {prof['nome_azienda']}")
        return True
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        return False


def main():
    """Esegui tutti i test"""
    print("=" * 60)
    print("🚀 BidPilot MVP - Installation Test")
    print("=" * 60)
    
    results = [
        ("Imports", test_imports()),
        ("Structure", test_structure()),
        ("Profilo", test_profilo())
    ]
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    for name, ok in results:
        print(f"{'✅' if ok else '❌'} {name}")
    
    print("\n" + "=" * 60)
    
    if all(r[1] for r in results):
        print("🎉 Installazione OK!")
        print("\nProssimi passi:")
        print("1. streamlit run app.py")
        print("2. Inserire API Key nella sidebar")
        print("3. Caricare PDF e analizzare")
    else:
        print("❌ Alcuni test falliti")
        print("\nSoluzioni:")
        print("1. pip install -r requirements.txt")
        print("2. Verificare file mancanti")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
