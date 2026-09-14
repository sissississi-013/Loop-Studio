"""A draft is a reviewable rendered artifact, not a mutation of the user's edit."""
import copy
import time
import re
from .core import Conflict, validate
from .media import export
from .providers import direct, analyze, InvalidProposal


def review(project, timeline, requested_duration):
    previous = {s['id']: s for s in project['timeline']}
    actual = sum(s['end'] - s['start'] for s in timeline)
    notes = []
    if abs(actual-requested_duration) > 1:
        notes.append(f'This cut is {actual:.1f}s versus the requested {requested_duration:.0f}s. Available moments and locked shots may limit the length.')
    repeated = 0
    for i, shot in enumerate(timeline):
        for other in timeline[:i]:
            if shot['asset_id'] == other['asset_id'] and min(shot['end'],other['end'])-max(shot['start'],other['start']) > .1:
                repeated += 1
                break
    if repeated:
        notes.append(f'{repeated} shots reuse footage already included in this draft.')
    changed = [s['id'] for s in timeline if s['id'] not in previous or s != previous[s['id']]]
    removed = [sid for sid in previous if sid not in {s['id'] for s in timeline}]
    return {'duration': actual, 'shots': len(timeline), 'changed': len(changed), 'removed': len(removed),
            'locked': sum(s.get('locked', False) for s in timeline), 'notes': notes,
            'checks': ['Valid source ranges', 'Locked shots preserved', 'Preview rendered from original footage']}


def make_film(store, pid, project, data, cancel, progress):
    started = time.monotonic()
    progress('1 / 3 · Finding moments — reusing footage already analyzed')
    draft_base = copy.deepcopy(project)
    data = {**data, 'enforce_duration': True}
    direction = interpret_direction(str(data.get('brief', project['brief'])), data.get('mood'))
    overrides = set(project.get('style_overrides', []))
    if data.get('mood') is None and not data.get('target_shot_id') and data.get('draft_timeline') is None:
        draft_base['style'].update({k:v for k,v in direction['style'].items() if k not in overrides})
    references = [a for a in project['assets'].values() if a.get('kind') == 'reference']
    missing_references = {a['id'] for a in references if a['id'] not in project['analysis']}
    if missing_references:
        progress('1 / 3 · Reading reference color and cut timing')
        analyze(store, pid, False, cancel, progress, missing_references)
        draft_base['analysis'] = store.load(pid)['analysis']
    if references and not data.get('draft_timeline') and not data.get('target_shot_id'):
        reference = references[-1]
        suggested = draft_base['analysis'][reference['id']].get('reference_style', {})
        draft_base['style'].update({k:v for k,v in suggested.items() if k in ('look','shot_seconds') and k not in overrides})
        direction['label'] += ' · Reference color/cut timing considered; manual choices preserved'
    if data.get('draft_timeline') is not None:
        store.apply(draft_base, {'op': 'proposal', 'timeline': data['draft_timeline'], 'style': data.get('draft_style', {})})
        validate(draft_base)
    if data.get('draft_timeline') is not None and not data.get('use_model'):
        proposal = revise_offline(draft_base, data)
    else:
        try:
            proposal = direct(store, pid, draft_base, data, cancel, progress)
        except InvalidProposal as error:
            if cancel.is_set():
                raise ValueError('Operation cancelled')
            progress('1 / 3 · Repairing an invalid plan once, using source-bound checks')
            repair = {**data, 'repair':{'error':str(error),'previous_response':error.proposal}}
            proposal = direct(store, pid, draft_base, repair, cancel, progress)
            proposal['repaired'] = True
    if not data.get('target_shot_id') and not data.get('draft_timeline') and not any(s.get('locked') for s in proposal['timeline']):
        remaining = float(data.get('duration', 30))
        fitted = []
        for shot in proposal['timeline']:
            if remaining < .25:
                break
            shot = copy.deepcopy(shot)
            shot['end'] = min(shot['end'], shot['start']+remaining)
            fitted.append(shot)
            remaining -= shot['end']-shot['start']
        proposal['timeline'] = fitted
        proposal['duration'] = sum(s['end']-s['start'] for s in fitted)
    candidate = copy.deepcopy(project)
    candidate['timeline'] = proposal['timeline']
    candidate['style'] = draft_base['style']
    proposal['style'] = copy.deepcopy(candidate['style'])
    proposal['direction'] = direction['label']
    validate(candidate)
    # Do not spend a render on a proposal that was already superseded during inference.
    if store.load(pid)['version'] != project['version']:
        raise Conflict('Your edit changed while the draft was being planned. Generate again from the latest version.')
    progress('2 / 3 · Making a watchable draft')
    rendered = export(store, pid, candidate, cancel,
                      lambda message: progress('2 / 3 · ' + message), preview=True, record=False)
    progress('3 / 3 · Checking the cut and preparing review')
    if cancel.is_set():
        raise ValueError('Operation cancelled')
    proposal['preview'] = rendered
    proposal['review'] = review(project, proposal['timeline'], float(data.get('duration', 30)))
    proposal['elapsed_seconds'] = round(time.monotonic()-started, 2)
    proposal['base_timeline'] = copy.deepcopy(project['timeline'])
    return proposal


def accept_film(store, pid, version, result):
    if result['version'] != version:
        raise Conflict('This draft belongs to an older edit. Make a fresh draft before keeping it.')
    with store.lock:
        project = store.update(pid, version, {'op': 'proposal', 'timeline': result['timeline'], 'style': result.get('style', {})})
        if result.get('preview'):
            project['accepted_preview'] = {**result['preview'], 'version': project['version']}
            store.save(project)
        return project


def revise_offline(project, data):
    instruction = str(data.get('feedback', data.get('brief', ''))).lower()
    timeline = copy.deepcopy(project['timeline'])
    eligible = [i for i,s in enumerate(timeline) if not s.get('locked')]
    if not eligible:
        raise ValueError('All shots are locked. Unlock a shot to revise it.')
    indices = eligible
    if re.search(r'\b(opening|first|intro)\b', instruction):
        indices = [0] if 0 in eligible else []
    elif re.search(r'\b(ending|last|outro)\b', instruction):
        indices = [len(timeline)-1] if len(timeline)-1 in eligible else []
    if not indices:
        raise ValueError('That part of the film is locked. Unlock it before revising.')
    if re.search(r"\b(don't|do not|not)\b", instruction):
        raise ValueError('For nuanced instructions, enable your vision model. Offline revisions support shorter, longer, mute, or reverse order.')
    if re.search(r'\b(shorter|shorten|faster)\b', instruction):
        for i in indices:
            shot = timeline[i]; shot['end'] = shot['start'] + max(.25, (shot['end']-shot['start'])*.7)
    elif re.search(r'\b(longer|extend|slower)\b', instruction):
        for i in indices:
            shot = timeline[i]; shot['end'] = min(project['assets'][shot['asset_id']]['duration'], shot['end']+1)
    elif re.search(r'\b(mute|silent)\b', instruction):
        for i in indices:
            timeline[i]['volume'] = 0
    elif 'reverse' in instruction:
        shots = [copy.deepcopy(timeline[i]) for i in reversed(eligible)]
        for i, shot in zip(eligible, shots):
            timeline[i] = shot
    else:
        raise ValueError('Offline revisions support shorter, longer, mute, or reverse order. Enable your vision model for story instructions.')
    if timeline == project['timeline']:
        raise ValueError('There is no extra source footage for that change. Try another trim or direction.')
    return {'version': project['version'], 'timeline': timeline, 'mode': 'signals',
            'duration': sum(s['end']-s['start'] for s in timeline),
            'rationale': 'Applied the supported timing/order instruction to the requested unlocked shots. Other shots were preserved.'}


def interpret_direction(brief, mood=None):
    if mood not in (None,'quiet','bright','editorial'):
        raise ValueError('Unknown creative direction')
    words=brief.lower()
    if mood=='quiet' or (mood is None and re.search(r'\b(quiet|gentle|calm|slow|understated)\b',words)):
        return {'label':'Quiet: longer moments, soft color and a restrained music bed',
                'style':{'look':'warm','font':'serif','shot_seconds':4,'music':'ambient','title_position':'bottom-left'}}
    if mood=='bright' or (mood is None and re.search(r'\b(music video|energetic|exciting|punchy|upbeat|playful|fast)\b',words)):
        return {'label':'Energetic: shorter cuts and an original electronic rhythm',
                'style':{'look':'natural','font':'sans','shot_seconds':1.25,'music':'pulse','title_position':'top-left'}}
    if mood=='editorial':
        return {'label':'Editorial: monochrome, clean typography and deliberate cuts',
                'style':{'look':'mono','font':'sans','shot_seconds':3,'music':'none','title_position':'bottom-left'}}
    return {'label':'Your chosen finishing settings', 'style':{}}
