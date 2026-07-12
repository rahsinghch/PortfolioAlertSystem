import anthropic
print([n for n in dir(anthropic) if 'response' in n.lower() or 'completion' in n.lower()])
print('Anthropic has responses:', hasattr(anthropic.Anthropic, 'responses'))
print('Anthropic has completions:', hasattr(anthropic.Anthropic, 'completions'))
