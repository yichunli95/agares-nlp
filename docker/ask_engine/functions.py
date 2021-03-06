#!/usr/bin/python3 -W ignore
# -*- coding:utf8 -*-
#/usr/bin/env python3

#!/usr/bin/env python3

import io
import nltk
import re
import spacy
import random
import pyinflect

from . import svo
#from svo import nlp, findSVOs


def open_document(file_path):
    with io.open(file_path, 'r', encoding='utf8') as f:
        document = f.read()
    document = re.sub('[\n]+', ' . ', document)
    return document


def tokenize_sentence(document):
    return nltk.sent_tokenize(document)


def find_verb(tok):
    head = tok.head
    while head.pos_ != "VERB" and head.head != head:
        head = head.head
    return head


def format_subject(ner_dict, sent, subject):
    subject_formatted = subject.split(' ')
    subject_formatted[0] = subject_formatted[0].lower()
    if (subject.lower() in ner_dict.keys() or subject_formatted[0] in ner_dict.keys()) or sent.find(subject.split(' ')[0])!=0:
        subject_formatted = subject
    else:
        subject_formatted = ' '.join(subject_formatted)
    return subject_formatted


def generate_why_dict(token, word_token):
    why_key_word = ['because']
    why_dict = {}
    for key in why_key_word:
        if key in word_token:
            try:
                index = word_token.index(key)
                tok = token[index]
                v = find_verb(tok).text
                if v not in why_dict:
                    why_dict[v] = []
                why_dict[v].append(key)
            except:
                continue
    return why_dict


def generate_when_and_where_dict(token, word_token):
    when_key_word = ['TIME', 'DATE']
    where_key_word = ['FAC', 'GPE', 'LOC']
    when_dict = {}
    where_dict = {}
    ner = [(tok.text, tok.label_) for tok in token.ents]
    ner_dict = {}
    for entity in ner:
        ner_dict[entity[0].lower()] = entity[1]

        if entity[1] in when_key_word:
            try:
                key = entity[0].lower()
                if ',' in key:
                    key = key.split(',')[0]
                if ' ' in key:
                    key = key.split(' ')[0]
                if '-' in key:
                    key = key.split('-')[0]
                index = word_token.index(key)
                tok = token[index]
                v = find_verb(tok).text
                if v not in when_dict:
                    when_dict[v] = []
                when_dict[v].append(entity[0])
            except:
                continue

        if entity[1] in where_key_word:
            try:
                key = entity[0].lower()
                if ',' in key:
                    key = key.split(',')[0]
                if ' ' in key:
                    key = key.split(' ')[0]
                if '-' in key:
                    key = key.split('-')[0]
                index = word_token.index(key)
                tok = token[index]
                v = find_verb(tok).text
                if v not in where_dict:
                    where_dict[v] = []
                where_dict[v].append(entity[0])
            except:
                continue
    return ner_dict, when_dict, where_dict


def generate_question_modifier(sent, subject, object, verb_modifier, exception_list):
    # generate question modifier
    start, end = len(sent), -1
    svo_end = max(sent.find(subject) + len(subject), sent.find(object) + len(object))
    for modifier in verb_modifier:
        idx = sent.find(' '.join(modifier.split(' ')[0:2]))
        if idx >= svo_end and modifier in exception_list:
            break
        if svo_end <= idx < start:
            start = idx
        if idx >= svo_end and idx + len(modifier) > end:
            end = idx + len(modifier)

    modifier_sent = sent[start:end + 1].strip()
    if modifier_sent != "":
        modifier_sent = " " + modifier_sent
    if modifier_sent and (modifier_sent[-1] == '.' or modifier_sent[-1] == ','):
        modifier_sent = modifier_sent[:-1]

    return modifier_sent


def generate_questions(document_path):
    document = open_document(document_path)
    sentences = tokenize_sentence(document)
    # sentences = sentences[0:10]
    who_key_word = ['he', 'she', 'they', 'him', 'her', 'them', 'who']
    question_set_why = set()
    question_set_when = set()
    question_set_where = set()
    question_set_what = set()
    question_set_who = set()
    question_set_TF = set()
    question_set_TF_IS_IT_TRUE = set()
    question_set_TF_passive = set()
    question_set_TF_passive_IS_IT_TRUE = set()
    question_length_limit = 50
    debug_printing = False

    for sent in sentences:
        # sent = "A study showed that of the 58 people who were present when the tomb and sarcophagus were opened, only eight died within a dozen years."
        # sent = 'Known as the Sleeping Pokémon, Snorlax has been said to weigh over 1,000 pounds and until Generation III was considered the heaviest known Pokémon.'
        token = svo.nlp(sent)
        if debug_printing:
            print("Sentence: ", token)
        word_token = [tok.lower_ for tok in token]
        # index = word_token.index("with")
        # print(token[index].pos_, token[index].dep_)
        # print(token[index].head)
        # for e in token[index].lefts:
        #     print(e, e.pos_, e.dep_)
        # for e in token[index].rights:
        #     print(e, e.pos_, e.dep_)
        why_dict = generate_why_dict(token, word_token)
        ner_dict, when_dict, where_dict = generate_when_and_where_dict(token, word_token)

        result = svo.findSVOs(token)
        if debug_printing:
            print("svo:", result)
            print("Questions:")
        for entity in result:
            subject, subject_tag, negation, verb, object, object_tag, verb_modifier = entity
            #to remove questions about pronouns
            if subject_tag == 'PRP' or object_tag == 'PRP' or subject_tag == 'PRP$' or object_tag == 'PRP$':
                continue
            #remove questions with subject starting with 'to'
            if subject.find('to') == 0 or subject.find('To') == 0:
                continue

            if subject.find('who')==0 or subject.find('which')==0 or subject.find('that')==0 or object.find('who')==0 or object.find('which')==0 or object.find('that')==0:
                continue

            if subject_tag not in ['NN','NNS','NNP','NNPS','default'] or object_tag not in ['NN','NNS','NNP','NNPS','default']:
                continue


            if subject != " ":
                subject = subject.strip()
                if subject[-1] == '.' or subject[-1] == ',':
                    subject = subject[:-1]
            if object != " ":
                object = object.strip()
                if object[-1] == '.' or object[-1] == ',':
                    object = object[:-1]

            subject_formatted = format_subject(ner_dict, sent, subject)
            object_formatted = format_subject(ner_dict, sent, object)
            # if negation!="":
            #     print(entity)
            if debug_printing:
                print(entity)
            # generate question about verb
            question_tense1 = ''
            question_tenseTF = ''
            what_tense = ''
            tense = verb.tag_
            if debug_printing:
                print(tense)
            plural = subject_tag == 'NNS' or subject_tag == 'NNPS'
            object_plural = object_tag == 'NNS' or object_tag == 'NNPS'

            verb_str = verb.text.lower()
            what_verb = verb.text.lower()
            if tense == 'VBD':
                question_tense1 = 'did'
                verb_str = verb.lemma_.lower()
                if object_plural:
                    question_tense_passive = 'were'
                else:
                    question_tense_passive = 'was'
            elif tense == 'VBG':
                if plural:
                    question_tense1 = 'are'
                    what_tense = 'are'
                    question_tenseTF = 'are'
                else:
                    question_tense1 = 'is'
                    what_tense = 'is'
                    question_tenseTF = 'is'
                if object_plural:
                    question_tense_passive = 'are'
                else:
                    question_tense_passive = 'is'
            elif tense == 'VBN':
                if plural:
                    question_tense1 = 'have'
                    what_tense = 'has'
                    question_tenseTF = 'have'
                else:
                    question_tense1 = 'has'
                    what_tense = 'has'
                    question_tenseTF = 'has'
                if object_plural:
                    question_tense_passive = 'are'
                else:
                    question_tense_passive = 'is'
            else:
                if plural:
                    question_tense1 = 'do'
                else:
                    question_tense1 = 'does'
                verb_str = verb.lemma_.lower()
                if object_plural:
                    question_tense_passive = 'are'
                else:
                    question_tense_passive = 'is'

            # generate why question
            if verb.text in why_dict:
                why_key_word = ['because']
                exception_list = []
                for modifier in verb_modifier:
                    for key_word in why_key_word:
                        if key_word in modifier:
                            exception_list.append(modifier)
                modifier_sent = generate_question_modifier(sent, subject, object, verb_modifier, exception_list)
                if subject != " ":
                    q = "Why " + question_tense1 + " " + subject_formatted + " " + verb_str + ("" if object_formatted == " " else " " + object_formatted) + modifier_sent + "?"
                    if len(q) >= question_length_limit:
                        if debug_printing:
                            print(q)
                        question_set_why.add(q)

            # generate when question
            if verb.text in when_dict:
                exception_list = []
                question_status = False
                for modifier in verb_modifier:
                    for ner in when_dict[verb.text]:
                        if ner in modifier:
                            question_status = True
                            exception_list.append(modifier)
                if question_status:
                    modifier_sent = generate_question_modifier(sent, subject, object, verb_modifier, exception_list)
                    if subject != " ":
                        q = "When " + question_tense1 + " " + subject_formatted + " " + verb_str + ("" if object_formatted == " " else " " + object_formatted) + modifier_sent + "?"
                        if len(q) >= question_length_limit:
                            if debug_printing:
                                print(q)
                            question_set_when.add(q)

            # generate where question
            if verb.text in where_dict:
                exception_list = []
                question_status = False
                for modifier in verb_modifier:
                    for ner in where_dict[verb.text]:
                        if "in " + ner in modifier or "at " + ner in modifier:
                            question_status = True
                            exception_list.append(modifier)
                if question_status:
                    modifier_sent = generate_question_modifier(sent, subject, object, verb_modifier, exception_list)
                    if subject != " ":
                        q = "Where " + question_tense1 + " " + subject_formatted + " " + verb_str + ("" if object_formatted == " " else " " + object_formatted) + modifier_sent + "?"
                        if len(q) >= question_length_limit:
                            if debug_printing:
                                print(q)
                            question_set_where.add(q)

            modifier_sent = generate_question_modifier(sent, subject, object, verb_modifier, [])

            # generate question about subject
            if subject != " ":
                question_type = "What"
                for k, v in ner_dict.items():
                    if k in subject.lower() and v == 'PERSON':
                        question_type = "Who"
                        break

                for key in who_key_word:
                    if subject.lower() == key:
                        question_type = "Who"
                        break
                if object != " ":
                    q = question_type + " " + ("" if what_tense == "" else what_tense + " ") + what_verb + (
                        "" if object_formatted == " " else " " + object_formatted) + modifier_sent + "?"
                    if len(q) >= question_length_limit:
                        if debug_printing:
                            print(q)
                        if question_type == 'Who':
                            question_set_who.add(q)
                        else:
                            question_set_what.add(q)

            # generate question about object
            if object != " ":
                question_type = "What"
                for k, v in ner_dict.items():
                    if k in object.lower() and v == 'PERSON':
                        question_type = "Who"
                        break

                for key in who_key_word:
                    if object.lower() == key:
                        question_type = "Who"
                        break

                if subject != " ":
                    q = question_type + " " + question_tense1 + (
                        "" if subject_formatted == " " else " " + subject_formatted) + " " + verb_str + modifier_sent + "?"
                # else:
                #     if verb._.inflect('VBN'):
                #         q = question_type + " " + question_tense_passive + " " + verb._.inflect('VBN').lower() + modifier_sent + "?"
                    if len(q) >= question_length_limit:
                        if debug_printing:
                            print(q)
                        if question_type == 'Who':
                            question_set_who.add(q)
                        else:
                            question_set_what.add(q)

            # generate T/F questions
            if subject != " ":
                q = "Is it true that " + subject_formatted + ("" if question_tenseTF == "" else " " + question_tenseTF) + " " + verb.text.lower() + ("" if object_formatted == " " else " " + object_formatted) + modifier_sent + "?"
                if len(q) >= question_length_limit:
                    if debug_printing:
                        print(q)
                    question_set_TF_IS_IT_TRUE.add(q)

                q = question_tense1[0].upper()+question_tense1[1:] + " " + subject_formatted + " " + verb_str + (
                        "" if object_formatted == " " else " " + object_formatted) + modifier_sent + "?"
                if len(q) >= question_length_limit:
                    if debug_printing:
                        print(q)
                    question_set_TF.add(q)

            if object != " ":
                if verb._.inflect('VBN'):
                    q = "Isn't it true that " + object_formatted + ("" if question_tense_passive == "" else " " + question_tense_passive) + " " + verb._.inflect('VBN').lower() + ("" if subject_formatted == " " else " by " + subject_formatted) + modifier_sent + "?"
                    if len(q) >= question_length_limit:
                        if debug_printing:
                            print(q)
                        question_set_TF_passive_IS_IT_TRUE.add(q)

                    q = question_tense_passive[0].upper()+question_tense_passive[1:] + " " + object_formatted + " " + verb._.inflect('VBN').lower() + (
                            "" if subject_formatted == " " else " by " + subject_formatted) + modifier_sent + "?"
                    if len(q) >= question_length_limit:
                        if debug_printing:
                            print(q)
                        question_set_TF_passive.add(q)

    question_set_TF_true = question_set_TF.union(question_set_TF_IS_IT_TRUE)
    question_set_TF_false = question_set_TF_passive.union(question_set_TF_passive_IS_IT_TRUE)
    return question_set_why, question_set_when, question_set_where, question_set_what, question_set_who, question_set_TF_true, question_set_TF_false


if __name__ == '__main__':
    # document_path = "../data/set1/a1.txt"
    # question_set = generate_questions(document_path)

    for s in range(1, 6):
        for a in range(1, 11):
            document_path = f"../data/set{s}/a{a}.txt"
            question_set_why, question_set_when, question_set_where, question_set_what, question_set_who, question_set_TF, question_set_TF_IS_IT_TRUE, question_set_TF_passive, question_set_TF_passive_IS_IT_TRUE  = generate_questions(document_path)
            print(random.sample(question_set_what, 1), s, a)
