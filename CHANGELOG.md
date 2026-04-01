# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [1.4.1] - 2026-04-01

### Fixed
- Hardware sensors (CPU, temperature) were always empty because the API query included the non-existent column `memoryUtilizationPercent`, causing the entire request to fail with HTTP 400
- Widened device-info query time window from 10 to 30 minutes for more reliable data

### Removed
- Memory Usage sensor (the LMC API does not expose `memoryUtilizationPercent` despite it being documented)

### Added
- Debug logging for device hardware data in coordinator
