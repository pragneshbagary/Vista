#!/bin/bash

# Deployment monitoring script for VISTA Personal AI RAG System
# This script monitors deployments and triggers rollback on failure

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_ROOT}/deployment-monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Monitoring configuration
CHECK_INTERVAL=30  # seconds
MAX_FAILURES=3
FAILURE_THRESHOLD=5  # percentage

# Logging functions
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

# Check health endpoint
check_health() {
    local api_url=$1
    local timeout=10
    
    if curl -sf --max-time $timeout "$api_url/health" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Get metrics
get_metrics() {
    local api_url=$1
    
    curl -s "$api_url/metrics" 2>/dev/null || echo "{}"
}

# Check error rate
check_error_rate() {
    local api_url=$1
    local threshold=$2
    
    local metrics=$(get_metrics "$api_url")
    local error_rate=$(echo "$metrics" | jq -r '.error_rate // 0')
    
    # Convert to percentage
    local error_percentage=$(echo "$error_rate * 100" | bc)
    
    if (( $(echo "$error_percentage > $threshold" | bc -l) )); then
        log_warning "High error rate detected: ${error_percentage}%"
        return 1
    else
        log_info "Error rate: ${error_percentage}%"
        return 0
    fi
}

# Check response time
check_response_time() {
    local api_url=$1
    local threshold=$2  # milliseconds
    
    local metrics=$(get_metrics "$api_url")
    local p95_time=$(echo "$metrics" | jq -r '.p95_response_time_ms // 0')
    
    if (( $(echo "$p95_time > $threshold" | bc -l) )); then
        log_warning "High response time detected: ${p95_time}ms (threshold: ${threshold}ms)"
        return 1
    else
        log_info "P95 response time: ${p95_time}ms"
        return 0
    fi
}

# Check database health
check_database_health() {
    local api_url=$1
    
    local health=$(curl -s "$api_url/health" | jq -r '.components.database.status // "unknown"')
    
    if [ "$health" != "healthy" ]; then
        log_warning "Database health: $health"
        return 1
    else
        log_info "Database health: $health"
        return 0
    fi
}

# Check LLM health
check_llm_health() {
    local api_url=$1
    
    local health=$(curl -s "$api_url/health" | jq -r '.components.llm.status // "unknown"')
    
    if [ "$health" != "healthy" ]; then
        log_warning "LLM health: $health"
        return 1
    else
        log_info "LLM health: $health"
        return 0
    fi
}

# Perform comprehensive health check
perform_health_check() {
    local api_url=$1
    local error_threshold=$2
    local response_threshold=$3
    
    log_info "Performing comprehensive health check..."
    
    local failures=0
    
    # Check health endpoint
    if ! check_health "$api_url"; then
        log_error "Health endpoint check failed"
        failures=$((failures + 1))
    else
        log_success "Health endpoint check passed"
    fi
    
    # Check error rate
    if ! check_error_rate "$api_url" "$error_threshold"; then
        failures=$((failures + 1))
    fi
    
    # Check response time
    if ! check_response_time "$api_url" "$response_threshold"; then
        failures=$((failures + 1))
    fi
    
    # Check database health
    if ! check_database_health "$api_url"; then
        failures=$((failures + 1))
    fi
    
    # Check LLM health
    if ! check_llm_health "$api_url"; then
        failures=$((failures + 1))
    fi
    
    return $failures
}

# Monitor deployment
monitor_deployment() {
    local environment=$1
    local api_url=$2
    local error_threshold=$3
    local response_threshold=$4
    local duration=$5  # monitoring duration in seconds
    
    log "Starting deployment monitoring for $environment..."
    log "API URL: $api_url"
    log "Error threshold: ${error_threshold}%"
    log "Response threshold: ${response_threshold}ms"
    log "Monitoring duration: ${duration}s"
    
    local start_time=$(date +%s)
    local consecutive_failures=0
    local total_checks=0
    local failed_checks=0
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [ $elapsed -ge $duration ]; then
            log_success "Monitoring period completed"
            break
        fi
        
        total_checks=$((total_checks + 1))
        
        if perform_health_check "$api_url" "$error_threshold" "$response_threshold"; then
            consecutive_failures=0
            log_success "Health check passed (check #$total_checks)"
        else
            failed_checks=$((failed_checks + 1))
            consecutive_failures=$((consecutive_failures + 1))
            log_error "Health check failed (check #$total_checks, consecutive failures: $consecutive_failures)"
            
            # Trigger rollback if too many consecutive failures
            if [ $consecutive_failures -ge $MAX_FAILURES ]; then
                log_error "Maximum consecutive failures reached ($MAX_FAILURES)"
                return 1
            fi
        fi
        
        # Calculate failure rate
        local failure_rate=$((failed_checks * 100 / total_checks))
        
        if [ $failure_rate -gt $FAILURE_THRESHOLD ]; then
            log_error "Failure rate exceeded threshold: ${failure_rate}% > ${FAILURE_THRESHOLD}%"
            return 1
        fi
        
        # Wait before next check
        sleep $CHECK_INTERVAL
    done
    
    # Final report
    local failure_rate=$((failed_checks * 100 / total_checks))
    log_info "Monitoring complete: $total_checks checks, $failed_checks failures (${failure_rate}%)"
    
    if [ $failure_rate -le $FAILURE_THRESHOLD ]; then
        log_success "Deployment monitoring passed"
        return 0
    else
        log_error "Deployment monitoring failed"
        return 1
    fi
}

# Continuous monitoring
continuous_monitoring() {
    local environment=$1
    local api_url=$2
    local error_threshold=$3
    local response_threshold=$4
    
    log "Starting continuous monitoring for $environment..."
    
    while true; do
        if ! perform_health_check "$api_url" "$error_threshold" "$response_threshold"; then
            log_error "Health check failed during continuous monitoring"
            return 1
        fi
        
        sleep $CHECK_INTERVAL
    done
}

# Generate monitoring report
generate_report() {
    local api_url=$1
    local output_file=$2
    
    log "Generating monitoring report..."
    
    {
        echo "=== Deployment Monitoring Report ==="
        echo "Generated: $(date)"
        echo ""
        echo "=== Health Status ==="
        curl -s "$api_url/health" | jq . || echo "Failed to get health status"
        echo ""
        echo "=== Metrics ==="
        curl -s "$api_url/metrics" | jq . || echo "Failed to get metrics"
        echo ""
        echo "=== Logs ==="
        tail -50 "$LOG_FILE"
    } > "$output_file"
    
    log_success "Report generated: $output_file"
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV       Environment to monitor (render, aws, docker)
    -u, --api-url URL          API URL to monitor
    -d, --duration SECONDS     Monitoring duration (default: 300)
    -c, --continuous           Continuous monitoring mode
    -r, --report FILE          Generate report to file
    --error-threshold PCT      Error rate threshold (default: 5)
    --response-threshold MS    Response time threshold (default: 1000)
    -h, --help                 Show this help message

Examples:
    # Monitor for 5 minutes
    $0 -e render -u https://api.yourdomain.com -d 300

    # Continuous monitoring
    $0 -e aws -u https://api.yourdomain.com -c

    # Generate report
    $0 -e docker -u https://api.yourdomain.com -r report.txt
EOF
}

# Parse command line arguments
main() {
    local environment=""
    local api_url=""
    local duration=300
    local continuous_mode=false
    local report_file=""
    local error_threshold=5
    local response_threshold=1000
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                environment="$2"
                shift 2
                ;;
            -u|--api-url)
                api_url="$2"
                shift 2
                ;;
            -d|--duration)
                duration="$2"
                shift 2
                ;;
            -c|--continuous)
                continuous_mode=true
                shift
                ;;
            -r|--report)
                report_file="$2"
                shift 2
                ;;
            --error-threshold)
                error_threshold="$2"
                shift 2
                ;;
            --response-threshold)
                response_threshold="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Validate required arguments
    if [ -z "$environment" ] || [ -z "$api_url" ]; then
        log_error "Missing required arguments"
        usage
        exit 1
    fi
    
    # Perform monitoring
    if [ "$continuous_mode" = true ]; then
        continuous_monitoring "$environment" "$api_url" "$error_threshold" "$response_threshold"
    else
        monitor_deployment "$environment" "$api_url" "$error_threshold" "$response_threshold" "$duration"
    fi
    
    # Generate report if requested
    if [ -n "$report_file" ]; then
        generate_report "$api_url" "$report_file"
    fi
}

# Run main function
main "$@"
