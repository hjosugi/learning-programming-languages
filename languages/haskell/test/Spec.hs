-- | Spec: a hand-rolled, base-only test runner.
--
-- The repo is OFFLINE, so we do not use Hspec/HUnit/QuickCheck (those would
-- need a hackage download). Instead we build a minimal assertion harness on top
-- of @base@: each check prints PASS/FAIL, and the process 'exitFailure's if any
-- check failed. This is enough to be a *real* test suite -- many cases,
-- including error and edge cases -- while staying runnable with plain runghc.
--
-- The upgrade path (README) shows how to swap this for Hspec + QuickCheck once
-- a package set is available.
module Main (main) where

import Calc
import Control.Monad (unless)
import Data.IORef (IORef, modifyIORef', newIORef, readIORef)
import System.Exit (exitFailure, exitSuccess)

-- A test result accumulator. We thread an IORef so each assertion can record
-- pass/fail without returning anything awkward.
data Stats = Stats { passed :: !Int, failed :: !Int }

-- | Generic equality assertion. 'Show' + 'Eq' on the expected type do the work.
assertEq :: (Eq a, Show a) => IORef Stats -> String -> a -> a -> IO ()
assertEq ref name expected actual
  | expected == actual = do
      modifyIORef' ref (\s -> s { passed = passed s + 1 })
      putStrLn ("PASS  " ++ name)
  | otherwise = do
      modifyIORef' ref (\s -> s { failed = failed s + 1 })
      putStrLn ("FAIL  " ++ name)
      putStrLn ("        expected: " ++ show expected)
      putStrLn ("        actual:   " ++ show actual)

-- | Assert a successful evaluation to (approximately) a number. We compare with
-- a tolerance because we evaluate to 'Double'.
assertEval :: IORef Stats -> String -> String -> Double -> IO ()
assertEval ref name input expected =
  case runCalc input of
    Right v
      | abs (v - expected) < 1e-9 -> do
          modifyIORef' ref (\s -> s { passed = passed s + 1 })
          putStrLn ("PASS  " ++ name)
    other -> do
      modifyIORef' ref (\s -> s { failed = failed s + 1 })
      putStrLn ("FAIL  " ++ name)
      putStrLn ("        input:    " ++ show input)
      putStrLn ("        expected: Right " ++ show expected)
      putStrLn ("        actual:   " ++ show other)

-- | Assert that an input fails with a specific 'CalcError'.
assertError :: IORef Stats -> String -> String -> CalcError -> IO ()
assertError ref name input expected =
  case runCalc input of
    Left e | e == expected -> do
      modifyIORef' ref (\s -> s { passed = passed s + 1 })
      putStrLn ("PASS  " ++ name)
    other -> do
      modifyIORef' ref (\s -> s { failed = failed s + 1 })
      putStrLn ("FAIL  " ++ name)
      putStrLn ("        input:    " ++ show input)
      putStrLn ("        expected: Left " ++ show expected)
      putStrLn ("        actual:   " ++ show other)

-- | Assert that an input fails, without caring which constructor (useful for
-- ParseError whose message text is an implementation detail).
assertFails :: IORef Stats -> String -> String -> (CalcError -> Bool) -> IO ()
assertFails ref name input ok =
  case runCalc input of
    Left e | ok e -> do
      modifyIORef' ref (\s -> s { passed = passed s + 1 })
      putStrLn ("PASS  " ++ name)
    other -> do
      modifyIORef' ref (\s -> s { failed = failed s + 1 })
      putStrLn ("FAIL  " ++ name)
      putStrLn ("        input:    " ++ show input)
      putStrLn ("        expected: a matching Left")
      putStrLn ("        actual:   " ++ show other)

isParseError :: CalcError -> Bool
isParseError (ParseError _) = True
isParseError _              = False

isLexError :: CalcError -> Bool
isLexError (LexError _) = True
isLexError _            = False

main :: IO ()
main = do
  ref <- newIORef (Stats 0 0)

  putStrLn "== tokenize =="
  assertEq ref "tokenize: simple"
    (Right [TNum 1, TOp Add, TNum 2])
    (tokenize "1 + 2")
  assertEq ref "tokenize: ignores whitespace"
    (Right [TNum 12, TOp Mul, TNum 3])
    (tokenize "  12*3 ")
  assertEq ref "tokenize: parens and ops"
    (Right [TLParen, TNum 1, TOp Sub, TNum 2, TRParen, TOp Pow, TNum 2])
    (tokenize "(1-2)^2")
  assertEq ref "tokenize: decimal literal"
    (Right [TNum 3.5])
    (tokenize "3.5")
  -- error/edge case in the lexer
  assertFails ref "tokenize: unexpected char is a LexError"
    "1 & 2" isLexError

  putStrLn "== parse (AST shape) =="
  assertEq ref "parse: precedence builds * under +"
    (Right (BinOp Add (Num 1) (BinOp Mul (Num 2) (Num 3))))
    (tokenize "1 + 2 * 3" >>= parse)
  assertEq ref "parse: left associativity of -"
    (Right (BinOp Sub (BinOp Sub (Num 1) (Num 2)) (Num 3)))
    (tokenize "1 - 2 - 3" >>= parse)
  assertEq ref "parse: right associativity of ^"
    (Right (BinOp Pow (Num 2) (BinOp Pow (Num 3) (Num 2))))
    (tokenize "2 ^ 3 ^ 2" >>= parse)
  assertEq ref "parse: unary minus"
    (Right (BinOp Add (Neg (Num 3)) (Num 4)))
    (tokenize "-3 + 4" >>= parse)
  assertEq ref "parse: parens override precedence"
    (Right (BinOp Mul (BinOp Add (Num 1) (Num 2)) (Num 3)))
    (tokenize "(1 + 2) * 3" >>= parse)

  putStrLn "== eval (numbers) =="
  assertEval ref "eval: precedence"          "1 + 2 * 3"     7
  assertEval ref "eval: grouping"            "(1 + 2) * 3"   9
  assertEval ref "eval: right-assoc power"   "2 ^ 3 ^ 2"     512
  assertEval ref "eval: unary minus"         "-3 + 4"        1
  assertEval ref "eval: fractional division" "10 / 4"        2.5
  assertEval ref "eval: nested negation"     "-(-(5))"       5
  assertEval ref "eval: whitespace-heavy"    "  2  +  2  "   4
  assertEval ref "eval: deep nesting"        "((1+2)*(3+4))" 21

  putStrLn "== eval (typed errors) =="
  assertError ref "eval: division by zero"
    "10 / (5 - 5)" DivByZero
  assertError ref "eval: power div-by-zero is fine (1/0 not hit)"
    "1 / 0" DivByZero
  assertFails ref "eval: dangling operator is ParseError"
    "1 +" isParseError
  assertFails ref "eval: empty input is ParseError"
    "" isParseError
  assertFails ref "eval: unbalanced paren is ParseError"
    "(1 + 2" isParseError
  assertFails ref "eval: trailing token is ParseError"
    "1 2" isParseError
  assertFails ref "eval: stray symbol is LexError"
    "1 + $" isLexError

  putStrLn "== Pretty typeclass + round-trip =="
  assertEq ref "pretty: operator"
    "+" (pretty Add)
  assertEq ref "pretty: fully parenthesized expr"
    "(1 + (2 * 3))"
    (either (const "<err>") pretty (tokenize "1 + 2 * 3" >>= parse))
  assertEq ref "pretty: error rendering"
    "evaluation error: division by zero"
    (pretty DivByZero)
  -- Round-trip property (by example): parse -> pretty -> parse -> eval is stable
  let roundTrip s = do
        e1 <- tokenize s >>= parse
        let printed = pretty e1
        e2 <- tokenize printed >>= parse
        v1 <- eval e1
        v2 <- eval e2
        pure (v1, v2)
  assertEq ref "round-trip: pretty output re-parses to same value"
    (Right (7.0, 7.0))
    (roundTrip "1 + 2 * 3")

  putStrLn "== Parser is a real Functor/Applicative/Monad =="
  -- Exercise the combinator instances directly on a token stream.
  let oneNum = runParser (fmap (\e -> e) numLit) [TNum 5]
        where numLit = Parser $ \ts -> case ts of
                (TNum n : rest) -> Right (Num n, rest)
                _               -> Left (ParseError "want num")
  assertEq ref "Functor: fmap over a parser"
    (Right (Num 5, [])) oneNum

  -- Monad/do via the public pipeline already covers >>= ; here check pure.
  assertEq ref "Applicative: pure injects without consuming"
    (Right (42 :: Int, [TNum 9]))
    (runParser (pure 42) [TNum 9])

  putStrLn "== batch higher-order helpers =="
  let batch = runAll ["1+1", "2*3", "1/0", "oops"]
  assertEq ref "runAll: maps runCalc over inputs (length preserved)"
    4 (length batch)
  assertEq ref "countOk: foldl' counts successful evals"
    2 (countOk batch)

  -- Final tally + exit code.
  Stats p f <- readIORef ref
  putStrLn "----------------------------------------"
  putStrLn ("Total: " ++ show (p + f) ++ "   passed: " ++ show p ++ "   failed: " ++ show f)
  unless (f == 0) $ do
    putStrLn "SUITE FAILED"
    exitFailure
  putStrLn "SUITE PASSED"
  exitSuccess
