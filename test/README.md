flowchart TD
    U[User] -->|call| T[extremeSearchTool.execute]
    T --> E[extremeSearch(prompt, dataStream)]
    E --> GO[generateObject (plan)]
    E --> GT[generateText (agent)]
    
    GT -->|uses tool:webSearch| WS[webSearch.execute]
    GT -->|uses tool:codeRunner| CR[codeRunner.execute]
    
    WS --> SW[searchWeb -> exa.searchAndContents]
    WS --> GC[getContents]
    GC --> EXA[exa.getContents]
    EXA -->|missing| FC[firecrawl.scrapeUrl]
    
    CR --> RC[runCode]
    RC --> DAY[Daytona sandbox: create/install/run/delete]
    
    GT -->|onStepFinish| TR[collect toolResults]
    E --> FINAL[汇总: text, toolResults, sources(去重/截断), charts]
    FINAL --> U
