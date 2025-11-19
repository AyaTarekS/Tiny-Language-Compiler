import sys
import os
from pathlib import Path
from typing import List, Tuple

# Token Type mapping for the TINY-like language
TOKEN_MAP = {
    ";": "SEMICOLON",
    "if": "IF",
    "then": "THEN",
    "else": "ELSE",
    "end": "END",
    "repeat": "REPEAT",
    "until": "UNTIL",
    ":=": "ASSIGN",
    "read": "READ",
    "write": "WRITE",
    "<": "LESSTHAN",
    "=": "EQUAL",
    "+": "PLUS",
    "-": "MINUS",
    "*": "MULT",
    "/": "DIV",
    "(": "OPENBRACKET",
    ")": "CLOSEDBRACKET",
    "IDENTIFIER": "IDENTIFIER",
    "NUMBER": "NUMBER"
}

#for reserved words and symbols
KEYWORDS = {"if", "then", "end", "repeat", "until", "read", "write"}
SPECIAL_SYMBOLS = {";", "+", "-", "*", "/", "(", ")", "<", "=", ":="}



##############################################FUNCTIONS####################################################################################


def get_token(line: str) -> Tuple[List[str], List[str]]:
    """
    Parses a line source code  into a list of Token objects.

    Args:
        line (str): The raw input string.

    Returns:
        Tuples[list[str], list[str]]: list of parsed tokens types and values.

    """

    tokens_type_list: List[str] = []
    tokens_value_list: List[str] = []
    
    # Ensure line is lowercase and remove leading whitespace
    line = line.lower().strip()
    length = len(line)
    i = 0  

    while i < length:
        char = line[i]

        # 1. Skip Whitespace
        if char.isspace():
            i += 1
            continue

        # 2. Skip Comments , comments are between {}
        if char == "{":
                # Find the closing brace from the current position
                end_comment = line.index("}", i)
                i = end_comment + 1
                continue

        # 3. Handle Numbers
        if char.isdigit():
            start = i
            i += 1
            # Continue advancing as long as the next character is a digit to save it as value
            while i < length and line[i].isdigit():
                i += 1
            
            value = line[start:i]
            tokens_value_list.append(value)
            tokens_type_list.append(TOKEN_MAP["NUMBER"])
            continue

        # 4. Handle Identifiers and Keywords
        if char.isalpha():
            start = i
            i += 1
            # Identifiers can contain ONLY letters 
            while i < length and (line[i].isalpha()):
                i += 1
            
            value = line[start:i]
            tokens_value_list.append(value)
            
            # Check if the parsed identifier is a reserved keyword
            if value in KEYWORDS:
                tokens_type_list.append(TOKEN_MAP[value])
            else:
                tokens_type_list.append(TOKEN_MAP["IDENTIFIER"])
            continue

        # 5. Handle Two-Character Symbols (:=)
        if char == ":" and i + 1 < length and line[i+1] == "=":
            tokens_value_list.append(":=")
            tokens_type_list.append(TOKEN_MAP[":="])
            i += 2
            continue

        # 6. Handle Single-Character Symbols
        if char in SPECIAL_SYMBOLS:
            tokens_value_list.append(char)
            tokens_type_list.append(TOKEN_MAP[char])
            i += 1 
            continue


    return tokens_type_list, tokens_value_list

def scanningFile(file_path: Path) -> Tuple[List[List[str]], List[List[str]], str]:
    """
    Parses source code  into a tuple of Token objects with the source code itself.

    Args:
        file_path (Path): The input file.

    Returns:
        Tuples[list[str], list[str], str]: list of parsed tokens types and values with the source code itself.
        
    """
    code_token_values: List[List[str]] = []
    code_token_types: List[List[str]] = []
    program_content = ""
    
    try:
        program_content = file_path.read_text(encoding='utf-8')
        print(f"--- Scanning file: {file_path.name} ---")

        #spliting the code by lines
        for line in program_content.strip().split('\n'):
            line_token_types, line_token_values = get_token(line)
            if line_token_types:
                code_token_types.append(line_token_types)
                code_token_values.append(line_token_values)

        return code_token_types, code_token_values, program_content
        
    except FileNotFoundError:
        print(f"Error: Input file not found at '{file_path}'")
        try:
            input("\nPress Enter to exit...")
        except EOFError:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred reading the file: {e}")
        try:
            input("\nPress Enter to exit...")
        except EOFError:
            pass
        sys.exit(1)


def main():


    prompt = "Please enter the file path without any (\"\") for the scanning operation:"
        
    input_path = Path(input(prompt))
    
    code_token_types, code_token_values, program_content = scanningFile(input_path)
    
    output_path = input_path.with_name(f"{input_path.stem}_tokens.txt")
    
    #Write the results to the output file
    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            #Write the source code in the output file
            outfile.write(f"--- Lexical Analysis of: {input_path.name} ---\n")
            outfile.write("-" * 50 + "\n")
            outfile.write(f"Source Program Content:\n{program_content}\n")
            outfile.write("-" * 50 + "\n\n")
            #Write the Tokens from the scanner
            outfile.write("--- Token Stream ---\n")
            for token_types, token_values in zip(code_token_types, code_token_values):
                for t_type, t_value in zip(token_types, token_values):
                    outfile.write(f"Type: {t_type:<12} Value: {t_value}\n")

        print(f"\n--- Scan Complete ---")
        print(f"Token list successfully written to: {output_path}")
        print(f"Output file location: {output_path.absolute()}")

    except Exception as e:
        print(f"Error writing output file to {output_path}: {e}")
        try:
            input("\nPress Enter to exit...")
        except EOFError:
            pass
        sys.exit(1)
        
    try:
        input("\nPress Enter to exit...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
