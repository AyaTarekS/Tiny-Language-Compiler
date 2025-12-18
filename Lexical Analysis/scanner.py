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

# for reserved words and symbols
KEYWORDS = {"if", "then", "end", "repeat", "until", "read", "write"}
SPECIAL_SYMBOLS = {";", "+", "-", "*", "/", "(", ")", "<", "=", ":="}


##############################################FUNCTIONS####################################################################################


def get_token(line: str, in_comment: bool) -> Tuple[List[str], List[str], bool]:
    """
    Parses a line of source code into a list of Tokens, respecting the comment state.

    Args:
        line (str): The raw input string line.
        in_comment (bool): True if currently inside a multi-line comment.

    Returns:
        Tuples[list[str], list[str], bool]: list of parsed tokens types and values,
                                            and the updated comment state.
    """

    tokens_type_list: List[str] = []
    tokens_value_list: List[str] = []

    # Ensure line is lowercase and remove leading/trailing whitespace
    line = line.lower().strip()
    length = len(line)
    i = 0

    while i < length:
        char = line[i]

        # 1. Handle Comments (High Priority)
        if in_comment:
            # We are currently inside a comment, search for the closing brace '}'
            end_comment_index = line.find("}", i)
            if end_comment_index != -1:
                # Comment block ends on this line
                in_comment = False
                i = end_comment_index + 1  # Start scanning after the closing brace
                continue
            else:
                # Comment continues to the next line (ignore the rest of this line)
                return tokens_value_list, tokens_type_list, True

        # 1b. Skip Whitespace only if not in a comment
        if char.isspace():
            i += 1
            continue

        # 1c. Handle start of a new comment (if not already in one, which is handled above)
        if char == "{":
            in_comment = True
            # Check if the comment ends on the same line
            end_comment_index = line.find("}", i)
            if end_comment_index != -1:
                # Single-line comment block
                in_comment = False
                i = end_comment_index + 1
            else:
                # Multi-line comment starts on this line, continues to the next
                # The rest of this line is ignored, and the state is returned as True
                return tokens_value_list, tokens_type_list, True
            continue

        # 3. Handle Numbers
        if char.isdigit():
            start = i
            i += 1
            # Continue advancing as long as the next character is a digit
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
            # Identifiers can contain ONLY letters (based on original intent, though TINY allows digits)
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
        if char == ":" and i + 1 < length and line[i + 1] == "=":
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
            
        # 7. Error Handling for unrecognized character (optional but good practice)
        print(f"Lexical Error: Unrecognized character '{char}' on line: {line}")
        i += 1
        
    return tokens_value_list, tokens_type_list, in_comment


def scanningFile(file_path: Path) -> Tuple[List[List[str]], List[List[str]]]:
    """
    Parses source code into a tuple of Token objects with the source code itself.

    Args:
        file_path (Path): The input file.

    Returns:
        Tuples[list[str], list[str]]: list of parsed tokens types and values with the source code itself.
        
    """
    code_token_values: List[List[str]] = []
    code_token_types: List[List[str]] = []
    program_content = ""
    # NEW: State variable to track if we are currently inside a multi-line comment
    in_comment = False 
    
    try:
        program_content = file_path.read_text(encoding='utf-8')
        print(f"--- Scanning file: {file_path.name} ---")

        # spliting the code by lines
        for line in program_content.strip().split('\n'):
            # Pass the current comment state and receive the new state
            line_token_values, line_token_types, in_comment = get_token(line, in_comment)
            
            # Only append tokens if some were found (i.e., line was not entirely a comment)
            if line_token_types:
                code_token_types.append(line_token_types)
                code_token_values.append(line_token_values)

        return code_token_values, code_token_types 
        
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
        
    # NOTE: For testing purposes in a controlled environment, 
    # you might need to mock the input if running outside a full terminal.
    # For a direct command line run, this is fine.
    try:
        input_raw = input(prompt)
    except EOFError:
        print("\nInput cancelled. Exiting.")
        sys.exit(0)
        
    input_path = Path(input_raw)
    
    code_token_values, code_token_types = scanningFile(input_path)
    
    output_path = input_path.with_name(f"{input_path.stem}_tokens.txt")
    
    # Write the results to the output file
    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            # main functionality: writing the tokens to the output file
            for token_types, token_values in zip(code_token_types, code_token_values):
                for t_type, t_value in zip(token_types, token_values):
                    outfile.write(f"{t_value},{t_type}\n")

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