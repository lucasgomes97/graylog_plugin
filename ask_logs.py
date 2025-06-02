from get_graylog_logs import get_logs
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from datetime import datetime, timezone
import re
import os
from dotenv import load_dotenv

# === CARREGAR VARIÁVEIS DE AMBIENTE ===
load_dotenv()

# === CONFIGURAÇÃO INFLUXDB ===
token = os.environ.get("INFLUXDB_TOKEN")
org = "IA"
url = "https://us-east-1-1.aws.cloud2.influxdata.com"
bucket = "Analises"

print(f"🔐 Token carregado: {'SIM' if token else 'NÃO'}")

client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)

# === FUNÇÃO PARA SALVAR NO INFLUXDB COM ID AUTOMÁTICO ===
def salvar_no_influx(erro, causa, solucao, criticidade, data_incidente, solucao_funcionou):
    try:
        query_api = client.query_api()

        query = f'''
        from(bucket: "{bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "logs_ai" and r._field == "id")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n:1)
        '''

        result = query_api.query(org=org, query=query)

        max_id = 0
        for table in result:
            for record in table.records:
                try:
                    max_id = int(record.get_value())
                except (ValueError, TypeError):
                    pass

        novo_id = max_id + 1

        ponto = (
            Point("logs_ai")
            .tag("erro_encontrado", erro[:50])  # erro como tag (opcional)
            .field("id", novo_id)
            .field("causa_provavel", causa)
            .field("solucao_sugerida", solucao)
            .field("criticidade", criticidade)
            .field("solucao_funcionou", solucao_funcionou)
            .field("data_incidente", data_incidente.isoformat())
            .time(datetime.now(timezone.utc))
        )

        write_api.write(bucket=bucket, org=org, record=ponto)
        print(f"✅ Log salvo no InfluxDB com id={novo_id}!")
    except Exception as e:
        print(f"❌ Erro ao salvar no InfluxDB: {e}")

# === CONFIGURAÇÃO DO LLM + BASE VETORIAL ===
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
db = FAISS.load_local("graylog_vector_index", embedding, allow_dangerous_deserialization=True)
retriever = db.as_retriever()
llm = ChatOpenAI(model="gpt-4", temperature=0)
qa_chain = RetrievalQA.from_chain_type(llm=llm, retriever=retriever)

# === CAPTURA DE LOGS DO GRAYLOG ===
logs = get_logs(query="error", range_secs=3600, limit=10)

if not logs:
    print("⚠️ Nenhum log encontrado.")
    exit()

logs_unidos = "\n\n".join(logs)

# === PROMPT DE ANÁLISE ===
prompt = f"""
Você é um especialista em análise de logs. Analise os logs abaixo e me responda em tópicos:
1. Qual o erro encontrado
2. Qual a causa provável
3. Qual a solução sugerida
4. Qual a criticidade (baixa, média ou alta)

Logs:
{logs_unidos}
"""

resposta = qa_chain.invoke(prompt)
print("\n🧠 Resposta do LLM:\n")
print(resposta["result"])

# === EXTRAÇÃO DOS CAMPOS DO TEXTO GERADO ===
erro = causa = solucao = criticidade = "Não identificado"

match_erro = re.search(r"1\.\s*(.+?)(?:\n|$)", resposta["result"])
match_causa = re.search(r"2\.\s*(.+?)(?:\n|$)", resposta["result"])
match_solucao = re.search(r"3\.\s*(.+?)(?:\n|$)", resposta["result"])
match_criticidade = re.search(r"4\.\s*(.+?)(?:\n|$)", resposta["result"])

if match_erro:
    erro = match_erro.group(1).strip()
if match_causa:
    causa = match_causa.group(1).strip()
if match_solucao:
    solucao = match_solucao.group(1).strip()
if match_criticidade:
    criticidade = match_criticidade.group(1).strip().lower()

# === ENTRADA MANUAL: SOLUÇÃO FUNCIONOU? ===
solucao_funcionou = input("A solução sugerida funcionou? (sim/não): ").strip().lower()
while solucao_funcionou not in ["sim", "não"]:
    solucao_funcionou = input("Por favor, responda 'sim' ou 'não': ").strip().lower()

data_incidente = datetime.now()

# === SALVA NO INFLUXDB ===
salvar_no_influx(erro, causa, solucao, criticidade, data_incidente, solucao_funcionou)

# === FINALIZAÇÃO ===
write_api.flush()
write_api.close()
client.close()
