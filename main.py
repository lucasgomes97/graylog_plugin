from get_graylog_logs import get_logs
from create_embeddings import embed_logs

def main():
    print("🔍 Buscando logs do Graylog...")
    logs = get_logs(query="error", range_secs=3600, limit=10)
    
    if not logs:
        print("⚠️ Nenhum log encontrado.")
        return

    print(f"✅ {len(logs)} logs encontrados. Gerando embeddings...")

    db = embed_logs(logs)

    print("🎉 Base vetorial criada com sucesso!")

    # Exemplo de similaridade
    query = "SocketError"
    results = db.similarity_search(query, k=3)

    print("\n🔎 Resultados semelhantes à consulta:")
    for result in results:
        print(result.page_content)
        print("-" * 80)

if __name__ == "__main__":
    main()
