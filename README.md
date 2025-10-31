# Tiny-Language-Compiler
This project provides a Simplified Compiler for TINY language by aiming to build a functional toolchain, starting with lexical analysis and moving through syntax analysis to support execution or translation for the language.
the project is implemented for Design of compilers Course (CSE439s) in Ain Shams university.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Inputs and Outputs](#Project-Inputs-and-Outputs)
3. [SetUP](#setup)
3. [Repository Structure](#repository-structure)
4. [License](#license)

---

## Overview
    The project implement lexical analysis and syntactic analysis stages, converting raw TINY source code into structured representations suitable for later compilation phases.

The project is structured into two levels:

- Level 1: Lexical Analysis (Scanner)
    The scanner is responsible for reading the source code of a TINY program and converting it into a sequence of tokens (identifiers, numbers, reserved words, operators, etc.). It correctly handles comments and whitespace.
- Level 2: Syntax Analysis (Parser with GUI)
    The parser will take the stream of tokens produced by the scanner and verify that the program adheres to the TINY language's grammar. 


---

## Project Inputs and Outputs

### Scanner Part

- Input:
A TINY source program written using TINY syntax (multiple lines of code).

- Processing:
1. Reads the input as stream of characters.

2. Groups characters into valid lexemes (identifiers, numbers, symbols, etc.).

3. Classifies each lexeme into its token type.

- Output:
A file containing a list of pairs in the form.

```bash
token_type , token_value
```

### Parser Part
To be implemented
- Input:
- Processing:
- Output:


---

### Setup

Follow these steps to set up and run the application:

1. **Ensure Python Installation**
   - Make sure you have Python version 3.11 or higher installed on your system.

2. **Clone the Repository**
   ```bash
   git clone https://github.com/AyaTarekS/Tiny-Language-Compiler/
   ```

3. **Install Required Libraries**
   Run the following commands to install the necessary dependencies:
   ```bash
   pip install PyInstaller
   ```

4. **Move the Main File**
   - Move the `Scanner.exe` file to the `Lexical analysis` folder.


5. **Navigate to the Required Directory**
   ```bash
   cd Tiny-Language-Compiler
   ```

6. **Run the Application in the CMD**
   ```bash
   ./scanner.exe "the code file path"
   ```
 
---

## Repository Structure

```markdown
Tiny-Language-Compiler/
├── Lexical Analysis/   # Scanner
│   ├── scanner.exe/   
│   └── scanner.py/            
├── Programs/            # Source code in tINY language
│   ├── Multiplication using addition.txt/
│   ├── Multiplication.txt/
│   ├── factorial.txt/
│   ├── isEven.txt/     
│   └── sum of N.txt/
│
├── Output Samples/       # Tokens stream for source code
│   ├── Multiplication using addition_tokens.txt/
│   ├── Multiplication_tokens.txt/
│   ├── factorial_tokens.txt/
│   ├── isEven_tokens.txt/     
│   └── sum of N_tokens.txt/
│
├── LICENSE         # License file
└── README.md       # Readme file
```

---

## License

This project is licensed under the [MIT](LICENSE).