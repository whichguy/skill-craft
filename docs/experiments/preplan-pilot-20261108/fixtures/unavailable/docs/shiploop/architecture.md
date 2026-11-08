# Architecture

## Stack

Python standard library; sqlite3 for local persistence where applicable.

## Structure

src/ holds current application adapters; tests/ holds baseline tests; data/ holds read-only seed inputs. New command and publication/search responsibility placement is undecided.

## Conventions

Small explicit functions, unittest, disposable fixtures.

## Interfaces and boundaries

The external service transport is unavailable and reveals no contract.

## Real-boundary checks

The requested command does not exist; its behavioral and recovery acceptance remains due after implementation.

## Decisions

AD-1: Preserve the supplied standard-library stack and existing baseline; accepted. New feature architecture remains provisional.

## Superseded

None.
