## Build frontend
cd components/chat_header/frontend
npm install
npm run build
cd ../../..

## Run
export OPENAI_API_KEY=sk-...
streamlit run app.py