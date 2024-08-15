import numpy as np
import pandas as pd
import torch
from datasets import load_dataset
import random
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sklearn.metrics import precision_score
from transformers import T5Tokenizer, T5ForConditionalGeneration
from transformers import XGLMTokenizer, XGLMForCausalLM

model_name = "google-t5/t5-small"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

# Load datasets
langs = ["en", "fr", "ru"]
dev_datasets = {}
test_datasets = {}

for lang in langs:
    dev_dataset = pd.read_csv(lang+'_corpora_train.tsv', sep='\t').drop(columns=['id', 'lang'])
    test_dataset = pd.read_csv(lang+'_corpora_test.tsv', sep='\t').drop(columns=['id', 'lang'])
    dev_datasets[lang] = dev_dataset.values.tolist()
    test_datasets[lang] = test_dataset.values.tolist()

choice_array = [
    "has-genre", "has-type", "has-parent", "invented-by", "is-member-of", "headquarters", 
    "has-occupation", "has-author", "invented-when", "from-country", "birth-place", 
    "movie-has-director", "org-has-founder", "has-population", "org-has-member", "has-edu", 
    "has-nationality", "is-where", "starring", "org-leader", "has-spouse", "has-sibling", 
    "won-award", "loc-leader", "has-child", "event-year", "has-weight", "has-height", 
    "has-length", "has-highest-mountain", "first-product", "has-tourist-attraction", 
    "has-lifespan", "no_relation", "eats", "post-code"
]

def format_example(text, entity1, entity2, label=None):
    prompt = f"Text: {text}\n Entity1: {entity1} \n Entity2: {entity2}\nRelation between entities is :\n"
    if label is not None:
        prompt += f" {label}\n"
    return prompt

def gen_prompt(source_lang, dev_data, k=5):
    prompt = f"Here are a few examples of text, entity 1, entity 2, and the relation between entity 1 and entity 2.\n\n"
    for number in random.sample(range(len(dev_data)), k):
        label = dev_data[number][-2]
        prompt += format_example(text=dev_data[number][-1], entity1=dev_data[number][0], entity2=dev_data[number][1], label=label)
    prompt += f"\nFor each example, specify the relationship between the given entities from the list: {', '.join(choice_array)}\n\n"
    return prompt

# Calculate precision
def calculate_precision(pred_labels, true_labels):
    return precision_score(true_labels, pred_labels, average='macro')

precisions = []
precString=[]
for source_lang in langs:
    for target_lang in langs:
        if source_lang != target_lang:
            pred_labels = []
            true_labels = []
            for i in range(100):
                few_shot_prompt = gen_prompt(source_lang, dev_data=dev_datasets[source_lang], k=2)
                query_input = test_datasets[target_lang][i]
                test_prompt = format_example(query_input[-1], query_input[0], query_input[1])
                prompt = f"Answer the relationship between entities for the given text:\n"
                final_prompt = f"{few_shot_prompt}{prompt}{test_prompt}".replace("<e1>", '').replace("<e2>", '').replace("</e1>", '').replace("</e2>", '')
                prompt_inputs = tokenizer(final_prompt, return_tensors="pt").input_ids
                outputs = model.generate(prompt_inputs)
                pred_label = tokenizer.decode(outputs[0], skip_special_tokens=True).lower()
                if query_input[-2] in pred_label:
                    pred_labels.append(query_input[-2])
                else: 
                    pred_labels.append(pred_label)
                true_labels.append(query_input[-2])
                
            precision = calculate_precision(pred_labels, true_labels)
            print(f"Precision for {source_lang}-{target_lang}: {precision}")
            precString.append(f"Precision for {source_lang}-{target_lang}: {precision}")
            precisions.append(precision)

# Calculate overall precision
overall_precision = np.mean(precisions)
for val in precString:
    print(val)
print(f"\nOverall precision across all language pairs: {overall_precision}")