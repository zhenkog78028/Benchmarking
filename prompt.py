def getPrompt(description:str, criteria:str, client, models: list[str]):
    prompts = []
    rubrics = []

    #I did a very minimal amount of prompt enineering here
    prompt = '''Create a benchmark test based on the following description and criteria:
Description: {description}
Criteria: {criteria}'''
    system_prompt = '''You are an AI benchmark creator. You are tasked with generating a prompt that satisfies the given description of a problem and criteria, and with generating a rubric has a program in python that can be ran to judge the solution. This prompt will be given to various AI models as a form of instruction to benchmark and their output, as is, will be evaluated by your rubric. Output ONLY the prompt and rubric, with only the specified formatting (no backticks, headers, other explanation text). Format your response exactly as follows: [your prompt here]<>[your rubric here]. The prompt should be designed to elicit a response that meets the criteria. The rubric should clearly outline how the response will be evaluated against the criteria.'''
    
    for llm in models:
        response = client.chat(model=llm, messages=[{'role': 'user', 'content': prompt, 'system': system_prompt, 'stream': 'false'}])
        if (response.message.content.startswith('```')):
            response.message.content=response.message.content[response.message.content.find('\n')+1:response.message.content.rfind('\n')] # strip first and last lines, https://stackoverflow.com/questions/28134319/fastest-way-to-remove-first-and-last-lines-from-a-python-string
        #I don't feel like doing robust parsing here, so I'm just going to assume the model follows instructions perfectly and splits the prompt and rubric with '<>'
        #we should do this once we get an actual list of models we want to use
        prompt, rubric = response.message.content.split('<>')
        prompts.append(prompt)
        rubrics.append(rubric)
    return prompts, rubrics