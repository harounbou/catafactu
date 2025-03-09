import streamlit as st
from openai import OpenAI
from sklearn.neighbors import NearestNeighbors
import pandas as pd
from modules.utils import fetch_df_from_db



class SalesAssistant:
    def __init__(self):
        self.client = OpenAI(api_key=st.secrets["openai"]["api_key"])
        self.transactions_df = fetch_df_from_db('transactions')

        if self.transactions_df.empty:
            st.error("Aucune transaction trouvée.")
            return
        

    def answer_question(self, question):
        """General Q&A using GPT-4"""
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": question}]
        )
        return response.choices[0].message.content

    def get_recommendations(self, current_items):
        """Item recommendations based on transaction history"""
        items_vector = pd.DataFrame([json.loads(t['items']) for t in self.transactions_df['items']]).explode()
        if items_vector.empty:
            return []
        pivot_table = items_vector.pivot_table(index='transaction_id', columns='denomination', values='Quantity', fill_value=0)
        model = NearestNeighbors(n_neighbors=3)
        model.fit(pivot_table)
        current_vector = pd.Series(0, index=pivot_table.columns)
        for item in current_items:
            if item['denomination'] in current_vector.index:
                current_vector[item['denomination']] = item['Quantity']
        distances, indices = model.kneighbors([current_vector])
        recommended_items = pivot_table.iloc[indices[0]].columns[pivot_table.iloc[indices[0]].sum() > 0].tolist()
        return [item for item in recommended_items if item not in [i['denomination'] for i in current_items]]
    


# Example usage in Streamlit
def run_assistant():
    assistant = SalesAssistant()
    st.write("### AI Sales Assistant")
    question = st.text_input("Posez une question sur les ventes :")
    if question:
        st.write(assistant.answer_question(question))
    
    if 'pos_state' in st.session_state and st.session_state['pos_state'].cart:
        recommendations = assistant.get_recommendations(st.session_state['pos_state'].cart)
        if recommendations:
            st.write("### Recommandations")
            for item in recommendations:
                st.write(f"- {item}")

if __name__ == "__main__":
    run_assistant()

