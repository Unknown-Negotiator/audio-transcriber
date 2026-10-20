#!/usr/bin/env python3
"""Dependency-free normalized word/character edit counts and alignments."""
import unicodedata

def normalize(text):
    text=unicodedata.normalize('NFKC',text).casefold()
    # Keep letters, combining marks, and numbers (including accents and Cyrillic ё).
    # Treat punctuation and symbols, including apostrophes and hyphens, as separators.
    return ' '.join(''.join(c if unicodedata.category(c)[0] in 'LNM' else ' ' for c in text).split())

def edits(reference,hypothesis,details=False):
    # Minimum Levenshtein alignment; ties prefer substitution, then deletion, insertion.
    m,n=len(reference),len(hypothesis)
    cost=[list(range(n+1))]+[[i]+[0]*n for i in range(1,m+1)]
    for i in range(1,m+1):
        for j in range(1,n+1):
            cost[i][j]=min(cost[i-1][j-1]+(reference[i-1]!=hypothesis[j-1]),cost[i-1][j]+1,cost[i][j-1]+1)
    counts={'substitutions':0,'deletions':0,'insertions':0,'correct':0,'reference_units':m,'hypothesis_units':n}
    operations=[];i,j=m,n
    while i or j:
        if i and j and reference[i-1]==hypothesis[j-1] and cost[i][j]==cost[i-1][j-1]:
            counts['correct']+=1;i-=1;j-=1
        elif i and j and cost[i][j]==cost[i-1][j-1]+1:
            counts['substitutions']+=1
            if details:operations.append({'op':'substitution','reference_index':i-1,'hypothesis_index':j-1,'reference':reference[i-1],'hypothesis':hypothesis[j-1]})
            i-=1;j-=1
        elif i and cost[i][j]==cost[i-1][j]+1:
            counts['deletions']+=1
            if details:operations.append({'op':'deletion','reference_index':i-1,'hypothesis_index':j,'reference':reference[i-1],'hypothesis':''})
            i-=1
        else:
            counts['insertions']+=1
            if details:operations.append({'op':'insertion','reference_index':i,'hypothesis_index':j-1,'reference':'','hypothesis':hypothesis[j-1]})
            j-=1
    counts['errors']=counts['substitutions']+counts['deletions']+counts['insertions']
    assert counts['errors']==cost[m][n]
    assert counts['correct']+counts['substitutions']+counts['deletions']==m
    assert counts['correct']+counts['substitutions']+counts['insertions']==n
    counts['error_rate']=counts['errors']/m if m else float(bool(n))
    if details:counts['operations']=list(reversed(operations))
    return counts

def score(reference,hypothesis):
    r,h=normalize(reference),normalize(hypothesis)
    return {'reference_normalized':r,'hypothesis_normalized':h,'word':edits(r.split(),h.split(),True),'character':edits(list(r),list(h))}

def aggregate(rows):
    result={}
    for unit in ['word','character']:
        values={k:sum(row['scores'][unit][k] for row in rows) for k in ['substitutions','deletions','insertions','correct','reference_units','hypothesis_units','errors']}
        values['error_rate']=values['errors']/values['reference_units']
        result[unit]=values
    result.update({'clips':len(rows),'audio_seconds':sum(row['audio_seconds'] for row in rows),'cli_wall_seconds':sum(row['wall_seconds'] for row in rows),'normalized_exact_match_clips':sum(row['scores']['reference_normalized']==row['scores']['hypothesis_normalized'] for row in rows)})
    result['real_time_factor_including_cli_startup']=result['cli_wall_seconds']/result['audio_seconds']
    return result

if __name__=='__main__':
    assert normalize('ÉCOLE — l’équipe, ПРИВЁТ!')=='école l équipe привёт'
    assert edits('a b c'.split(),'a x c y'.split())=={'substitutions':1,'deletions':0,'insertions':1,'correct':2,'reference_units':3,'hypothesis_units':4,'errors':2,'error_rate':2/3}
    assert edits('a b c'.split(),'a c'.split())['deletions']==1
    assert edits([],['x'])['insertions']==1
    assert score('Hello, world!','hello world')['word']['error_rate']==0
    print('Metric unit checks passed')
