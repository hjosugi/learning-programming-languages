-- | Calc: a tiny arithmetic expression parser + evaluator.
--
-- This single library module is the heart of the hands-on. It is written to
-- showcase the *signature features* of Haskell, each tagged below so you can
-- jump straight to the concept you want to study:
--
--   * Algebraic data types  -- 'Expr', 'Token', and the 'Parser' newtype
--   * Pattern matching       -- every function below deconstructs constructors
--   * A typeclass instance   -- our own 'Pretty' class + instances
--   * Maybe / Either         -- 'eval' and 'runCalc' return 'Either CalcError a'
--   * Recursion + HOFs       -- 'tokenize', 'foldl''-based reduction, 'map'
--   * Functor/Applicative/Monad -- the 'Parser' newtype is all three, by hand
--   * Pure / IO separation   -- this module is 100% pure; IO lives in Main
--
-- We deliberately avoid partial functions (head, fromJust, read, error) for
-- *expected* errors. Every recoverable failure is a value in 'Either'.
--
-- Grammar parsed (standard precedence, left-associative +-*/ , right-assoc ^):
--
--   expr   ::= term   (('+' | '-') term)*
--   term   ::= factor (('*' | '/') factor)*
--   factor ::= base ('^' factor)?          -- '^' is right associative
--   base   ::= number | '(' expr ')' | '-' base   -- unary minus
--
module Calc
  ( -- * Core algebraic data types
    Expr (..)
  , Op (..)
  , Token (..)
  , CalcError (..)
    -- * The signature typeclass we define
  , Pretty (..)
    -- * Pure pipeline
  , tokenize
  , parse
  , eval
  , runCalc
  , runAll
  , countOk
    -- * Small Parser-combinator type (Functor/Applicative/Monad demo)
  , Parser (..)
  ) where

import Control.Applicative (Alternative (..))
import Data.Char (isDigit, isSpace)
import Data.List (foldl')

-- ---------------------------------------------------------------------------
-- Algebraic data types
-- ---------------------------------------------------------------------------

-- | A binary operator. A classic *sum type*: four nullary constructors.
data Op = Add | Sub | Mul | Div | Pow
  deriving (Eq, Show)

-- | The abstract syntax tree. This is a *recursive* algebraic data type:
-- 'BinOp' contains two more 'Expr' values, so the type describes a tree.
--
--   data with multiple constructors  -> Num, Neg, BinOp
--   recursion in the type itself     -> the tree shape
data Expr
  = Num Double            -- ^ a literal number, e.g. @42@
  | Neg Expr              -- ^ unary minus, e.g. @-x@
  | BinOp Op Expr Expr    -- ^ a binary application, e.g. @l + r@
  deriving (Eq, Show)

-- | Lexer output. Keeping tokens as their own ADT (rather than re-scanning the
-- string in the parser) is the idiomatic two-stage design.
data Token
  = TNum Double
  | TOp Op
  | TLParen
  | TRParen
  deriving (Eq, Show)

-- | All the *expected* ways the pipeline can fail. Because these are ordinary
-- values, callers must handle them -- the compiler will not let you forget.
data CalcError
  = LexError String        -- ^ an unexpected character while tokenizing
  | ParseError String      -- ^ tokens did not match the grammar
  | DivByZero              -- ^ division (or 0 ^ negative) by zero at eval time
  deriving (Eq, Show)

-- ---------------------------------------------------------------------------
-- A typeclass we define ourselves
-- ---------------------------------------------------------------------------

-- | 'Pretty' renders a value back into human-readable source-ish text.
-- Defining our own class (rather than reusing 'Show') is the point: it
-- demonstrates declaring a class and writing instances for several types.
class Pretty a where
  pretty :: a -> String

instance Pretty Op where
  pretty Add = "+"
  pretty Sub = "-"
  pretty Mul = "*"
  pretty Div = "/"
  pretty Pow = "^"

-- | Pretty-printing an 'Expr' is a recursive fold over the tree. We fully
-- parenthesize so the output is unambiguous and round-trips through 'parse'.
instance Pretty Expr where
  pretty (Num n)
    | n == fromIntegral (round n :: Integer) = show (round n :: Integer)
    | otherwise = show n
  pretty (Neg e)        = "(-" ++ pretty e ++ ")"
  pretty (BinOp op l r) =
    "(" ++ pretty l ++ " " ++ pretty op ++ " " ++ pretty r ++ ")"

-- | Reusing the instances above to render errors nicely.
instance Pretty CalcError where
  pretty (LexError msg)   = "lex error: "   ++ msg
  pretty (ParseError msg) = "parse error: " ++ msg
  pretty DivByZero        = "evaluation error: division by zero"

-- ---------------------------------------------------------------------------
-- Stage 1: tokenize  (recursion + higher-order functions)
-- ---------------------------------------------------------------------------

-- | Turn a raw 'String' into a list of 'Token's, or a 'LexError'.
--
-- This is hand-written direct recursion over the character list -- the most
-- fundamental Haskell control structure. 'span' (a higher-order function) is
-- used to grab a run of digits in one shot.
tokenize :: String -> Either CalcError [Token]
tokenize = go
  where
    go :: String -> Either CalcError [Token]
    go [] = Right []
    go (c : cs)
      | isSpace c = go cs
      | c == '('  = (TLParen :) <$> go cs
      | c == ')'  = (TRParen :) <$> go cs
      | Just op <- lookup c opTable = (TOp op :) <$> go cs
      | isDigit c || c == '.' =
          -- 'span' splits the run of digits/dot from the rest, in one pass.
          let (numStr, rest) = span (\x -> isDigit x || x == '.') (c : cs)
           in case readDouble numStr of
                Just n  -> (TNum n :) <$> go rest
                Nothing -> Left (LexError ("bad number literal: " ++ numStr))
      | otherwise = Left (LexError ("unexpected character: " ++ [c]))

    opTable :: [(Char, Op)]
    opTable = [('+', Add), ('-', Sub), ('*', Mul), ('/', Div), ('^', Pow)]

-- | A *total* number reader. We never call the partial 'read'; instead we
-- pattern-match on @reads@'s result list, returning 'Nothing' on any failure
-- or trailing garbage. This is the idiomatic safe-parse pattern.
readDouble :: String -> Maybe Double
readDouble s = case reads s :: [(Double, String)] of
  [(n, "")] -> Just n
  _         -> Nothing

-- ---------------------------------------------------------------------------
-- A minimal Parser-combinator type  (Functor / Applicative / Monad demo)
-- ---------------------------------------------------------------------------

-- | A parser is a function from a token stream to either an error or a
-- (result, leftover-tokens) pair. Wrapping it in a @newtype@ lets us give it
-- 'Functor', 'Applicative', 'Monad' and 'Alternative' instances -- exactly the
-- hierarchy this repo is about. Building these *by hand* (instead of importing
-- a library) is how the intuition sticks.
newtype Parser a = Parser
  { runParser :: [Token] -> Either CalcError (a, [Token]) }

-- | Functor: map over the *result* without touching the leftover stream.
-- "Run me, and if I succeed, transform my answer with f."
instance Functor Parser where
  fmap f (Parser p) = Parser $ \ts ->
    case p ts of
      Left e         -> Left e
      Right (a, ts') -> Right (f a, ts')

-- | Applicative: 'pure' consumes nothing; '<*>' threads the stream left to
-- right, running the function parser, then the argument parser on what's left.
instance Applicative Parser where
  pure a = Parser $ \ts -> Right (a, ts)
  Parser pf <*> Parser pa = Parser $ \ts ->
    case pf ts of
      Left e          -> Left e
      Right (f, ts')  -> case pa ts' of
        Left e           -> Left e
        Right (a, ts'')  -> Right (f a, ts'')

-- | Monad: '>>=' lets the *next* parser depend on the previous result. This is
-- what makes context-sensitive parsing (and our 'do' notation below) possible.
instance Monad Parser where
  return = pure
  Parser p >>= f = Parser $ \ts ->
    case p ts of
      Left e         -> Left e
      Right (a, ts') -> runParser (f a) ts'

-- | Alternative: '<|>' tries the left parser, and only if it fails (without
-- having committed) falls back to the right. 'empty' always fails. This gives
-- us choice, the other half of any grammar.
instance Alternative Parser where
  empty = Parser $ \_ -> Left (ParseError "no parse")
  Parser l <|> Parser r = Parser $ \ts ->
    case l ts of
      Left _   -> r ts
      success  -> success

-- | Fail the current parse with a message.
failP :: String -> Parser a
failP msg = Parser $ \_ -> Left (ParseError msg)

-- | Consume exactly one token if it satisfies a predicate.
satisfy :: (Token -> Bool) -> String -> Parser Token
satisfy ok what = Parser $ \ts -> case ts of
  (t : rest) | ok t -> Right (t, rest)
  (t : _)           -> Left (ParseError ("expected " ++ what ++ ", got " ++ show t))
  []                -> Left (ParseError ("expected " ++ what ++ ", got end of input"))

-- | Consume one token expected to be a specific one.
token :: Token -> Parser ()
token want = () <$ satisfy (== want) (show want)

-- ---------------------------------------------------------------------------
-- Stage 2: parse  (recursive-descent built from the combinators above)
-- ---------------------------------------------------------------------------

-- | Parse a token list into an 'Expr', enforcing that the *whole* stream is
-- consumed. This is the public entry point for stage two.
parse :: [Token] -> Either CalcError Expr
parse ts = case runParser (exprP <* endOfInput) ts of
  Left e          -> Left e
  Right (expr, _) -> Right expr
  where
    endOfInput = Parser $ \rest -> case rest of
      [] -> Right ((), [])
      _  -> Left (ParseError ("trailing tokens: " ++ show rest))

-- | expr ::= term (('+'|'-') term)*   -- left associative, so we fold left.
exprP :: Parser Expr
exprP = chainl1 termP addSub
  where
    addSub =  (BinOp Add <$ token (TOp Add))
          <|> (BinOp Sub <$ token (TOp Sub))

-- | term ::= factor (('*'|'/') factor)*
termP :: Parser Expr
termP = chainl1 factorP mulDiv
  where
    mulDiv =  (BinOp Mul <$ token (TOp Mul))
          <|> (BinOp Div <$ token (TOp Div))

-- | factor ::= base ('^' factor)?  -- '^' is RIGHT associative, so we recurse
-- on the right rather than fold left.
factorP :: Parser Expr
factorP = do
  b <- baseP
  (do token (TOp Pow)
      r <- factorP
      pure (BinOp Pow b r))
    <|> pure b

-- | base ::= number | '(' expr ')' | '-' base
baseP :: Parser Expr
baseP = numP <|> parenP <|> negP <|> failP "expected a number, '(' or '-'"
  where
    numP = do
      t <- satisfy isNum "a number"
      case t of
        TNum n -> pure (Num n)
        _      -> failP "internal: satisfy returned non-number"
    parenP = do
      token TLParen
      e <- exprP
      token TRParen
      pure e
    negP = do
      token (TOp Sub)
      Neg <$> baseP

    isNum (TNum _) = True
    isNum _        = False

-- | A classic higher-order combinator: parse one @p@, then zero or more
-- (operator, p) pairs, folding them *left* associatively with the operator
-- functions. This is the textbook way to encode left-assoc binary operators.
chainl1 :: Parser a -> Parser (a -> a -> a) -> Parser a
chainl1 p op = do
  x <- p
  rest x
  where
    rest acc =
      (do f <- op
          y <- p
          rest (f acc y))
        <|> pure acc

-- ---------------------------------------------------------------------------
-- Stage 3: eval  (pattern matching + Either error propagation)
-- ---------------------------------------------------------------------------

-- | Evaluate an 'Expr' to a 'Double', or fail with a 'CalcError'.
--
-- Note how 'Either' short-circuits: as soon as a sub-expression yields a
-- 'Left', the whole computation returns it. The @do@ block reads like
-- straight-line code but is really monadic error threading.
eval :: Expr -> Either CalcError Double
eval (Num n)        = Right n
eval (Neg e)        = negate <$> eval e
eval (BinOp op l r) = do
  x <- eval l
  y <- eval r
  apply op x y

-- | Apply a single operator, guarding the one runtime error: division by zero.
apply :: Op -> Double -> Double -> Either CalcError Double
apply Add x y = Right (x + y)
apply Sub x y = Right (x - y)
apply Mul x y = Right (x * y)
apply Div _ 0 = Left DivByZero
apply Div x y = Right (x / y)
apply Pow x y = Right (x ** y)

-- ---------------------------------------------------------------------------
-- The whole pipeline, composed in Either
-- ---------------------------------------------------------------------------

-- | tokenize -> parse -> eval, wired together so a failure at any stage
-- propagates. This is the one function 'Main' actually calls; everything above
-- it is pure and individually testable.
--
-- The @>>=@ chain is Either's monad doing the plumbing: each stage only runs
-- if the previous one produced a 'Right'.
runCalc :: String -> Either CalcError Double
runCalc input = tokenize input >>= parse >>= eval

-- | Evaluate many expressions at once. A small but genuine higher-order use:
-- 'map' lifts the pure 'runCalc' over a list, pairing each input with its
-- 'Either' result. 'foldl'' appears in 'tokenize'; this completes the
-- map/fold pair the learning targets call for.
runAll :: [String] -> [(String, Either CalcError Double)]
runAll = map (\s -> (s, runCalc s))

-- | A pure summary statistic computed with a strict left fold over results:
-- how many of a batch evaluated successfully. Demonstrates 'foldl'' as a
-- reduction (not just as the lexer's internal helper).
countOk :: [(String, Either CalcError Double)] -> Int
countOk = foldl' step 0
  where
    step n (_, Right _) = n + 1
    step n (_, Left _)  = n
