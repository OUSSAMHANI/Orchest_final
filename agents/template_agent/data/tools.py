# Current existing tools, can be enhancend for later use
EXISTANT_TOOLS = {
    # "read_file":{
    #     "description":"Reading the file ",
    #     "input_schema":{
    #         "type":"object",
    #         "properties":{
    #             "file_path":{
    #                 "type":"string",
    #                 "description":"The path to the file to read"
    #             }
    #         },
    #         "required":["file_path"]
    #     }
    # },
    "ast_analysis": {
        "description": "Analyzing the file system structure and AST tools",
        "analyzed_files": {
            "parser.py": {
                "methods": [
                "parse_file"
                ],
                "parse_file": {
                "description": "Parsing the file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to parse"
                    }
                    },
                    "required": ["file_path"]
                },
                "output_schema": {
                    "file": "string",
                    "imports": "array",
                    "top_level_functions": "array",
                    "classes": "array"
                }
                }
            },
            "tools.py": {
                "methods": [
                "analyze_file_ast",
                "list_workspace_symbols",
                "get_ast_tools"
                ],
                "analyze_file_ast": {
                "description": "Analyzing the file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "The path to the file to analyze"
                    }
                    },
                    "required": ["file_path"]
                },
                "output_schema": {
                    "file": "string",
                    "imports": "array",
                    "top_level_functions": "array",
                    "classes": "array"
                }
                },
                "list_workspace_symbols": {
                "description": "Listing the symbols in the workspace",
                "input_schema": {
                    "type": "object",
                    "properties": {
                    "workspace_path": {
                        "type": "string",
                        "description": "The path to the workspace to list"
                    }
                    },
                    "required": ["workspace_path"]
                },
                "output_schema": {
                    "file": "string",
                    "imports": "array",
                    "top_level_functions": "array",
                    "classes": "array"
                }
                },
                "get_ast_tools": {
                "description": "Getting the AST tools from langchain",
                "input_schema": {
                    "type": "object",
                    "properties": {
                    "workspace_path": {
                        "type": "string",
                        "description": "The path to the workspace to list"
                    }
                    },
                    "required": ["workspace_path"]
                },
                "output_schema": {
                    "file": "string",
                    "imports": "array",
                    "top_level_functions": "array",
                    "classes": "array"
                }
                }
            }
        }
    },
    "docker":{
        "description":"Using docker as a sandbox to run the code ",
        "analyzed_files":{
            "sandbox.py":{
                "methods":[
                    "run_tests_in_sandbox"
                ],
                "run_tests_in_sandbox":{
                    "description":"Running the tests in the sandbox",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "workspace_path":{
                                "type":"string",
                                "description":"The path to the workspace to run"
                            }
                        },
                        "required":["workspace_path"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "files":{
        "description":"Using files to read and write the file ",
        "analyzed_files":{
            "file_tools.py":{
                "methods":[
                    "get_file_tools"
                ],
                "get_file_tools":{
                    "description":"Getting the file tools from langchain",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "workspace_dir":{
                                "type":"string",
                                "description":"The path to the workspace directory"
                            }
                        },
                        "required":["workspace_dir"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "folders":{
        "description":"Creating a folder ",
        "analyzed_files":{
            "folder_tools.py":{
                "methods":[
                    "initiate_directory",
                    "clear_directory"
                ],
                "initiate_directory":{
                    "description":"Initiating a directory",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "workspace_dir":{
                                "type":"string",
                                "description":"The path to the workspace directory"
                            }
                        },
                        "required":["workspace_dir"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                },
                "clear_directory":{
                    "description":"Clearing a directory",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "workspace_dir":{
                                "type":"string",
                                "description":"The path to the workspace directory"
                            }
                        },
                        "required":["workspace_dir"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "git":{
        "description":"Using git to commit the changes ",
        "analyzed_files":{
            "git_tools.py":{
                "methods":[
                    "clone_or_pull_repo",
                    "create_branch",
                    "commit_and_push"
                ],
                "clone_or_pull_repo":{
                    "description":"Cloning the repository",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "repo_url":{
                                "type":"string",
                                "description":"The URL of the repository to clone"
                            }
                        },
                        "required":["repo_url"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                },
                "create_branch":{
                    "description":"Creating a new branch",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "branch_name":{
                                "type":"string",
                                "description":"The name of the branch to create"
                            },
                            "repo_url":{
                                "type":"string",
                                "description":"The URL of the repository"
                            }
                        },
                        "required":["branch_name","repo_url"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                },
                "commit_and_push":{
                    "description":"Committing and pushing the changes",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "commit_message":{
                                "type":"string",
                                "description":"The commit message"
                            },
                            "branch_name":{
                                "type":"string",
                                "description":"The name of the branch to commit to"
                            },
                            "repo_url":{
                                "type":"string",
                                "description":"The URL of the repository"
                            },
                            "force":{
                                "type":"boolean",
                                "description":"Whether to force the push"
                            }
                        },
                        "required":["commit_message","branch_name","repo_url","force"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "github":{
        "description":"Using github to commit the changes ",
        "analyzed_files":{
            "issue_tools.py":{
                "methods":[
                    "list_open_issues",
                    "assign_issue"
                ],
                "list_open_issues":{
                    "description":"Listing open issues",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "max_results":{
                                "type":"integer",
                                "description":"The maximum number of issues to return"
                            }
                        },
                        "required":["max_results"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                },
                "assign_issue":{
                    "description":"Assigning an issue",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "issue_number":{
                                "type":"integer",
                                "description":"The issue number to assign"
                            }
                        },
                        "required":["issue_number"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            },
            "pr_tools.py":{
                "methods":[
                    "create_pull_request"
                ],
                "create_pull_request":{
                    "description":"Creating a pull request",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "branch_name":{
                                "type":"string",
                                "description":"The name of the branch to create"
                            },
                            "title":{
                                "type":"string",
                                "description":"The title of the pull request"
                            },
                            "body":{
                                "type":"string",
                                "description":"The body of the pull request"
                            },
                            "base_branch":{
                                "type":"string",
                                "description":"The base branch"
                            }
                        },
                        "required":["branch_name","title","body","base_branch"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "gitlab":{
        "description":"Using gitlab to commit the changes ",
        "analyzed_files":{
            "issue_tools.py":{
                "methods":[
                    "list_open_issues",
                    "assign_issue"
                ],
                "list_open_issues":{
                    "description":"Listing open issues",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "max_results":{
                                "type":"integer",
                                "description":"The maximum number of issues to return"
                            }
                        },
                        "required":["max_results"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                },
                "assign_issue":{
                    "description":"Assigning an issue",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "issue_number":{
                                "type":"integer",
                                "description":"The issue number to assign"
                            }
                        },
                        "required":["issue_number"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            },
            "pr_tools.py":{
                "methods":[
                    "create_pull_request"
                ],
                "create_pull_request":{
                    "description":"Creating a pull request",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "branch_name":{
                                "type":"string",
                                "description":"The name of the branch to create"
                            },
                            "title":{
                                "type":"string",
                                "description":"The title of the pull request"
                            },
                            "body":{
                                "type":"string",
                                "description":"The body of the pull request"
                            },
                            "base_branch":{
                                "type":"string",
                                "description":"The base branch"
                            }
                        },
                        "required":["branch_name","title","body","base_branch"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "graph_rag":{
        "description":"Using graph_rag to commit the changes ",
        "analyzed_files":{
            "tools.py":{
                "methods":[
                    "query_code_graph",
                    "summarise_code_graph"
                ],
                "query_code_graph":{
                    "description":"Querying the code knowledge graph",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "query":{
                                "type":"string",
                                "description":"The query to search for"
                            },
                            "workspace_path":{
                                "type":"string",
                                "description":"The workspace path"
                            }
                        },
                        "required":["query","workspace_path"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                },
                "summarise_code_graph":{
                    "description":"Summarising the code knowledge graph",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "workspace_path":{
                                "type":"string",
                                "description":"The workspace path"
                            }
                        },
                        "required":["workspace_path"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "linter":{
        "description":"Using linter to commit the changes ",
        "analyzed_files":{
            "tools.py":{
                "methods":[
                    "run_linter"
                ],
                "run_linter":{
                    "description":"Running the linter",
                    "input_schema":{
                        "type":"object",
                        "properties":{
                            "workspace_path":{
                                "type":"string",
                                "description":"The workspace path"
                            }
                        },
                        "required":["workspace_path"]
                    },
                    "output_schema":{
                        "file":"string",
                        "imports":"array",
                        "top_level_functions":"array",
                        "classes":"array"
                    }
                }
            }
        }
    },
    "search": {
        "description": "Using search to find information using DuckDuckGo",
        "analyzed_files": {
            "tools.py": {
                "methods": [
                    "search"
                ],
                "search": {
                    "description": "Searching the web",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The query to search for"
                            }
                        },
                        "required": ["query"]
                    },
                    "output_schema": {
                        "file": "string",
                        "imports": "array",
                        "top_level_functions": "array",
                        "classes": "array"
                    }
                }
            }
        }
    }
}