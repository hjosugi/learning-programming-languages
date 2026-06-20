-- | Main: the only place in this project that performs IO.
--
-- This demonstrates the *purity & IO separation* learning target. All the
-- actual logic lives in the pure 'Calc' module (no IO type anywhere in it).
-- Here we do exactly three IO-ish things:
--
--   1. decide where input comes from (argv or a built-in demo),
--   2. push each input string through the pure 'runCalc',
--   3. print the result and pick an exit code.
--
-- The pure core can be tested without any IO at all (see test/Spec.hs).
module Main (main) where

import Calc (Pretty (..), runCalc)
import System.Environment (getArgs)
import System.Exit (exitFailure, exitSuccess)

-- | Format one line of output for a single expression. This is *pure*: it takes
-- the input and the computed result and returns the text to print. Keeping it
-- pure means the formatting is unit-testable and IO stays trivial.
formatLine :: String -> Either e Double -> (String, e -> String) -> String
formatLine input result (label, prettyErr) =
  case result of
    Right v  -> label ++ input ++ "  =>  " ++ showNum v
    Left err -> label ++ input ++ "  =>  " ++ prettyErr err
  where
    showNum n
      | n == fromIntegral (round n :: Integer) = show (round n :: Integer)
      | otherwise = show n

-- | Built-in demo expressions, including deliberate error cases so the demo
-- shows both success and the typed-error path.
demoInputs :: [String]
demoInputs =
  [ "1 + 2 * 3"          -- precedence: 7
  , "(1 + 2) * 3"        -- grouping:   9
  , "2 ^ 3 ^ 2"          -- right assoc: 512, not 64
  , "-3 + 4"             -- unary minus: 1
  , "10 / 4"             -- fractional: 2.5
  , "10 / (5 - 5)"       -- DivByZero (typed error)
  , "1 + "               -- ParseError
  , "1 + $"              -- LexError
  ]

main :: IO ()
main = do
  args <- getArgs
  -- The pure boundary: turn raw strings into rendered lines, no IO involved.
  let inputs = if null args then demoInputs else [unwords args]
      rendered =
        [ formatLine inp (runCalc inp) ("  ", pretty) | inp <- inputs ]
      anyFailure = any (\inp -> isLeft (runCalc inp)) inputs

  putStrLn "Calc -- arithmetic expression evaluator"
  putStrLn "---------------------------------------"
  mapM_ putStrLn rendered

  -- Exit code reflects whether every expression evaluated. When the user
  -- supplies their own single expression, a parse/eval error is a real failure.
  if not (null args) && anyFailure
    then exitFailure
    else exitSuccess

-- | Local 'isLeft' so we depend on @base@ only (Data.Either.isLeft exists but
-- keeping it here keeps the import surface minimal and explicit).
isLeft :: Either a b -> Bool
isLeft (Left _)  = True
isLeft (Right _) = False
