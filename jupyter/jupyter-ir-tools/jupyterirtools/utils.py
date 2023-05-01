from IPython.display import display,Javascript, Markdown

def display_results_status(title, results, f = lambda x: 1):
    display(Markdown(f"### {title}")) 
    
    headers = ["status"]
    for result in results:
        for k in result:
            if not k in headers:
                headers.append(k)
                

    grid = "|"
    for header in headers:
        grid += f"{header}|"
    grid += f"\n|"
    for header in headers:
        grid += f"-----|"
        
    grid += f"\n"  
    
    for result in results:
        r = f(result)
        
        first = True
        grid += f"|"
        
        for header in headers:
            if first:
                color = "red"
                if r == 1:
                     color = "green"
                elif r == 2:
                     color = "orange"

                grid += f"<span style=\"color:{color}\"> &#9679;</span>|"
                first = False
            elif header in result:
                grid += f"{result[header]}|"
            else: 
                grid += f"&nbsp;|"
        grid += f"\n"
   
    display(Markdown(grid)) 