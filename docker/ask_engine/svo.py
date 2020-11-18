#!/usr/bin/python3 -W ignore::DeprecationWarning
# -*- coding:utf8 -*-
import spacy
from collections.abc import Iterable

# dependency markers for subjects
SUBJECTS = {"nsubj", "nsubjpass", "csubj", "csubjpass", "agent", "expl"}
# dependency markers for objects
OBJECTS = {"dobj", "dative", "attr", "oprd"}
# POS tags that will break adjoining items
BREAKER_POS = {"CCONJ", "VERB"}
# words that are negations
NEGATIONS = {"no", "not", "n't", "never", "none"}
verb_modifier = {"advcl", "prepc", "purpcl"}
nlp = spacy.load('en_core_web_sm')


def contains_conj(depSet):
    conj = ["and", "or", "nor", "but", "yet", "so", "for"]
    for e in conj:
        if e in depSet:
            return True
    return False


# get subs joined by conjunctions
def _get_subs_from_conjunctions(subs):
    more_subs = []
    for sub in subs:
        # rights is a generator
        rights = list(sub.rights)
        rightDeps = {tok.lower_ for tok in rights}
        if contains_conj(rightDeps):
            more_subs.extend([tok for tok in rights if tok.dep_ in SUBJECTS or tok.pos_ == "NOUN"])
            if len(more_subs) > 0:
                more_subs.extend(_get_subs_from_conjunctions(more_subs))
    return more_subs


# get objects joined by conjunctions
def _get_objs_from_conjunctions(objs):
    more_objs = []
    for obj in objs:
        # rights is a generator
        rights = list(obj.rights)
        rightDeps = {tok.lower_ for tok in rights}
        if contains_conj(rightDeps):
            more_objs.extend([tok for tok in rights if tok.dep_ in OBJECTS or tok.pos_ == "NOUN"])
            if len(more_objs) > 0:
                more_objs.extend(_get_objs_from_conjunctions(more_objs))
    return more_objs


# find sub dependencies
def _find_subs(tok):
    return [], False
    # head = tok.head
    # while head.pos_ != "VERB" and head.pos_ != "NOUN" and head.head != head:
    #     head = head.head
    # if head.pos_ == "VERB":
    #     subs = [tok for tok in head.lefts if tok.dep_ == "SUB"]
    #     if len(subs) > 0:
    #         verb_negated = _is_negated(head)
    #         subs.extend(_get_subs_from_conjunctions(subs))
    #         return subs, verb_negated
    #     elif head.head != head:
    #         return _find_subs(head)
    # elif head.pos_ == "NOUN":
    #     return [head], _is_negated(tok)
    # return [], False


# is the tok set's left or right negated?
def _is_negated(tok):
    parts = list(tok.lefts) + list(tok.rights)
    for dep in parts:
        if dep.lower_ in NEGATIONS:
            return True
    return False


# get all the verbs on tokens with negation marker
def _find_svs(tokens):
    svs = []
    verbs = [tok for tok in tokens if tok.pos_ == "VERB"]
    for v in verbs:
        subs, verbNegated = _get_all_subs(v)
        if len(subs) > 0:
            for sub in subs:
                svs.append((sub.orth_, "!" + v.orth_ if verbNegated else v.orth_))
    return svs


# get grammatical objects for a given set of dependencies (including passive sentences)
def _get_objs_from_prepositions(deps, is_pas):
    objs = []
    for dep in deps:
        if dep.pos_ == "ADP" and (dep.dep_ == "prep" or (is_pas and dep.dep_ == "agent")):
            objs.extend([tok for tok in dep.rights if tok.dep_  in OBJECTS or
                         (tok.pos_ == "PRON" and tok.lower_ == "me") or
                         (is_pas and tok.dep_ == 'pobj')])
    return objs


# xcomp; open complement - verb has no suject
def _get_obj_from_xcomp(deps, is_pas):
    for dep in deps:
        if dep.pos_ == "VERB" and dep.dep_ == "xcomp":
            v = dep
            rights = list(v.rights)
            objs = [tok for tok in rights if tok.dep_ in OBJECTS]
            objs.extend(_get_objs_from_prepositions(rights, is_pas))
            if len(objs) > 0:
                return v, objs
    return None, None


# get all functional subjects adjacent to the verb passed in
def _get_all_subs(v):
    verb_negated = _is_negated(v)
    subs = [tok for tok in v.lefts if tok.dep_ in SUBJECTS and tok.pos_ != "DET"]
    if len(subs) > 0:
        subs.extend(_get_subs_from_conjunctions(subs))
    else:
        foundSubs, verb_negated = _find_subs(v)
        subs.extend(foundSubs)
    if len(subs) == 0:
        subs.append(' ')
    return subs, verb_negated


# is the token a verb?  (excluding auxiliary verbs)
def _is_non_aux_verb(tok):
    return tok.pos_ == "VERB" and (tok.dep_ != "aux" and tok.dep_ != "auxpass")


# return the verb to the right of this verb in a CCONJ relationship if applicable
# returns a tuple, first part True|False and second part the modified verb if True
def _right_of_verb_is_conj_verb(v):
    # rights is a generator
    rights = list(v.rights)

    # VERB CCONJ VERB (e.g. he beat and hurt me)
    if len(rights) > 1 and rights[0].pos_ == 'CCONJ':
        for tok in rights[1:]:
            if _is_non_aux_verb(tok):
                return True, tok

    return False, v


# get all objects for an active/passive sentence
def _get_all_objs(v, is_pas):
    # rights is a generator
    rights = list(v.rights)

    objs = [tok for tok in rights if tok.dep_ in OBJECTS or (is_pas and tok.dep_ == 'pobj')]
    # objs.extend(_get_objs_from_prepositions(rights, is_pas))

    # potential_new_verb, potential_new_objs = _get_obj_from_xcomp(rights, is_pas)
    # if potential_new_verb is not None and potential_new_objs is not None and len(potential_new_objs) > 0:
    #     objs.extend(potential_new_objs)
    #     v = potential_new_verb
    if len(objs) > 0:
        objs.extend(_get_objs_from_conjunctions(objs))
    if len(objs) == 0:
        objs.append(' ')
    return v, objs


# return true if the sentence is passive - at he moment a sentence is assumed passive if it has an auxpass verb
def _is_passive(v):
    tokens = list(v.lefts) + list(v.rights)
    for tok in tokens:
        if tok.dep_ == "auxpass":
            return True
    return False


# resolve a 'that' where/if appropriate
def _get_that_resolution(item, toks):
    for tok in toks:
        if 'that' in [t.orth_ for t in tok.lefts]:
            return tok.head
    return item


# simple stemmer using lemmas
def _get_lemma(word: str):
    tokens = nlp(word)
    if len(tokens) == 1:
        return tokens[0].lemma_
    return word


# print information for displaying all kinds of things of the parse tree
def printDeps(toks):
    for tok in toks:
        print(tok.orth_, tok.dep_, tok.pos_, tok.head.orth_, [t.orth_ for t in tok.lefts], [t.orth_ for t in tok.rights])


# expand an obj / subj np using its chunk
def expand(item, tokens, visited, level):
    if item.lower_ == 'that' and level == 0:
        item = _get_that_resolution(item, tokens)

    parts = []
    if item.i in visited:
        return parts

    visited.add(item.i)
    if hasattr(item, 'lefts'):
        for part in item.lefts:
            if level == 0:
                if part.pos_ in BREAKER_POS:
                    break
            if not part.lower_ in NEGATIONS:
                parts.extend(expand(part, tokens, visited, level + 1))

    parts.append(item)

    if hasattr(item, 'rights'):
        for part in item.rights:
            if level == 0:
                if part.pos_ in BREAKER_POS:
                    break
            if not part.lower_ in NEGATIONS:
                parts.extend(expand(part, tokens, visited, level + 1))

    return parts


# convert a list of tokens to a string
def to_str(tokens):
    if isinstance(tokens, Iterable):
        return ' '.join([item.text for item in tokens])
    else:
        return ''


def get_modifier(tok, visited):
    modifier = []
    children = list(tok.lefts) + list(tok.rights)
    for e in children:
        if e.dep_ in verb_modifier:
            modifier.append(to_str(expand_modifier(e)))
        elif e.dep_ == "prep":
            # expand_status = True
            # for e_children in e.rights:
            #     if e_children.i in visited:
            #         expand_status = False
            #         break
            # if expand_status:
            modifier.append(to_str(expand_modifier(e)))
        elif e.pos_ == "VERB":
            expand_status = False
            for e_children in e.lefts:
                if e_children.dep_ == "advmod":
                    expand_status = True
                    break
            for e_children in e.rights:
                if e_children.dep_ == "advmod":
                    expand_status = True
                    break
            if expand_status:
                modifier.append(to_str(expand_modifier(e)))
    return modifier


def expand_modifier(item):
    parts = []
    if hasattr(item, 'lefts'):
        for part in item.lefts:
            parts.extend(expand_modifier(part))

    parts.append(item)

    if hasattr(item, 'rights'):
        for part in item.rights:
            parts.extend(expand_modifier(part))

    return parts


# find verbs and their subjects / objects to create SVOs, detect passive/active sentences
def findSVOs(tokens):
    svos = []
    verbs = [tok for tok in tokens if _is_non_aux_verb(tok)]
    for v in verbs:
        subs, verbNegated = _get_all_subs(v)
        is_pas = _is_passive(v)
        # hopefully there are subs, if not, don't examine this verb any longer
        if len(subs) > 0:
            # print(v.lemma_, v.tag_, subs)
            isConjVerb, conjV = _right_of_verb_is_conj_verb(v)
            if isConjVerb:
                v2, objs = _get_all_objs(conjV, is_pas)
                for sub in subs:
                    for obj in objs:
                        visited = set()  # recursion detection
                        visited.add(v.i)
                        visited.add(v2.i)
                        if isinstance(sub, str):
                            subject = ' '
                            subject_tag = 'default'
                        else:
                            subject = to_str(expand(sub, tokens, visited, 0))
                            subject_tag = sub.tag_

                        if isinstance(obj, str):
                            object = ' '
                            object_tag = 'default'
                            objNegated = False
                        else:
                            object = to_str(expand(obj, tokens, visited, 0))
                            object_tag = obj.tag_
                            objNegated = _is_negated(obj)

                        if is_pas:  # reverse object / subject for passive
                            svos.append((object, object_tag,
                                         "not" if verbNegated or objNegated else "",
                                         v, subject, get_modifier(v, visited) + get_modifier(v2, visited)))
                            svos.append((object, object_tag,
                                         "not" if verbNegated or objNegated else "",
                                         v2, subject, get_modifier(v, visited) + get_modifier(v2, visited)))
                        else:
                            svos.append((subject, subject_tag,
                                         "not" if verbNegated or objNegated else "",
                                         v, object, get_modifier(v, visited) + get_modifier(v2, visited)))
                            svos.append((subject, subject_tag,
                                         "not" if verbNegated or objNegated else "",
                                         v2, object_tag, get_modifier(v, visited) + get_modifier(v2, visited)))
            else:
                v, objs = _get_all_objs(v, is_pas)
                for sub in subs:
                    for obj in objs:
                        visited = set()  # recursion detection
                        visited.add(v.i)
                        if isinstance(sub, str):
                            subject = ' '
                            subject_tag = 'default'
                        else:
                            subject = to_str(expand(sub, tokens, visited, 0))
                            subject_tag = sub.tag_

                        if isinstance(obj, str):
                            object = ' '
                            object_tag = 'default'
                            objNegated = False
                        else:
                            object = to_str(expand(obj, tokens, visited, 0))
                            object_tag = obj.tag_
                            objNegated = _is_negated(obj)

                        if is_pas:  # reverse object / subject for passive
                            svos.append((object, object_tag,
                                         "not" if verbNegated or objNegated else "",
                                         v, subject, get_modifier(v, visited)))
                        else:
                            svos.append((subject, subject_tag,
                                         "not" if verbNegated or objNegated else "",
                                         v, object, get_modifier(v, visited)))
    return svos
