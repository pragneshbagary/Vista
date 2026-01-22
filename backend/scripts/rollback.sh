#!/bin/bash

# Rollback automation script for VISTA Personal AI RAG System
# This script handles automatic and manual rollback of deployments

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${PROJECT_ROOT}/rollback.log"
DEPLOYMENT_HISTORY="${PROJECT_ROOT}/.deployment-history"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Initialize deployment history
init_deployment_history() {
    if [ ! -f "$DEPLOYMENT_HISTORY" ]; then
        mkdir -p "$(dirname "$DEPLOYMENT_HISTORY")"
        echo "[]" > "$DEPLOYMENT_HISTORY"
    fi
}

# Record deployment
record_deployment() {
    local environment=$1
    local version=$2
    local status=$3
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    log "Recording deployment: $environment $version $status"
    
    # This would typically write to a database or file
    # For now, we'll just log it
    echo "$timestamp | $environment | $version | $status" >> "$DEPLOYMENT_HISTORY"
}

# Get previous version
get_previous_version() {
    local environment=$1
    
    # Get the second-to-last deployment for this environment
    grep "| $environment |" "$DEPLOYMENT_HISTORY" | tail -2 | head -1 | awk '{print $3}'
}

# Detect deployment failure
detect_deployment_failure() {
    local environment=$1
    local api_url=$2
    local max_retries=5
    local retry_count=0
    
    log "Detecting deployment failure for $environment..."
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -sf "$api_url/health" > /dev/null 2>&1; then
            log_success "Health check passed"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        log_warning "Health check failed (attempt $retry_count/$max_retries)"
        sleep 10
    done
    
    log_error "Deployment failure detected: health check failed after $max_retries attempts"
    return 1
}

# Rollback Render deployment
rollback_render() {
    local target_version=$1
    
    log "Rolling back Render deployment to $target_version..."
    
    if [ -z "$RENDER_DEPLOY_HOOK_ROLLBACK" ]; then
        log_error "RENDER_DEPLOY_HOOK_ROLLBACK not configured"
        return 1
    fi
    
    # Trigger rollback deploy hook
    if curl -X POST "$RENDER_DEPLOY_HOOK_ROLLBACK"; then
        log_success "Render rollback triggered"
        sleep 30
        return 0
    else
        log_error "Failed to trigger Render rollback"
        return 1
    fi
}

# Rollback AWS deployment
rollback_aws() {
    local target_version=$1
    
    log "Rolling back AWS deployment to $target_version..."
    
    if [ -z "$AWS_ECS_CLUSTER" ] || [ -z "$AWS_ECS_SERVICE" ]; then
        log_error "AWS_ECS_CLUSTER or AWS_ECS_SERVICE not configured"
        return 1
    fi
    
    # Get previous task definition
    local task_def=$(aws ecs describe-services \
        --cluster "$AWS_ECS_CLUSTER" \
        --services "$AWS_ECS_SERVICE" \
        --query 'services[0].taskDefinition' \
        --output text)
    
    if [ -z "$task_def" ]; then
        log_error "Failed to get current task definition"
        return 1
    fi
    
    # Get previous task definition revision
    local previous_revision=$((${task_def##*:} - 1))
    local previous_task_def="${task_def%:*}:$previous_revision"
    
    log "Reverting to task definition: $previous_task_def"
    
    # Update service with previous task definition
    if aws ecs update-service \
        --cluster "$AWS_ECS_CLUSTER" \
        --service "$AWS_ECS_SERVICE" \
        --task-definition "$previous_task_def"; then
        
        log "Waiting for service to stabilize..."
        if aws ecs wait services-stable \
            --cluster "$AWS_ECS_CLUSTER" \
            --services "$AWS_ECS_SERVICE"; then
            log_success "AWS rollback completed"
            return 0
        else
            log_error "Service failed to stabilize"
            return 1
        fi
    else
        log_error "Failed to update ECS service"
        return 1
    fi
}

# Rollback Docker deployment
rollback_docker() {
    local target_version=$1
    local compose_file="${PROJECT_ROOT}/docker-compose.prod.yml"
    
    log "Rolling back Docker deployment to $target_version..."
    
    if [ ! -f "$compose_file" ]; then
        log_error "docker-compose.prod.yml not found"
        return 1
    fi
    
    # Update image tag in docker-compose file
    sed -i.bak "s/vista-api:.*/vista-api:$target_version/" "$compose_file"
    
    # Pull new image
    if docker-compose -f "$compose_file" pull; then
        log "Docker image pulled successfully"
    else
        log_error "Failed to pull Docker image"
        # Restore backup
        mv "$compose_file.bak" "$compose_file"
        return 1
    fi
    
    # Restart services
    if docker-compose -f "$compose_file" up -d; then
        log_success "Docker services restarted"
        sleep 10
        return 0
    else
        log_error "Failed to restart Docker services"
        # Restore backup
        mv "$compose_file.bak" "$compose_file"
        return 1
    fi
}

# Verify rollback
verify_rollback() {
    local environment=$1
    local api_url=$2
    local max_retries=30
    local retry_count=0
    
    log "Verifying rollback for $environment..."
    
    while [ $retry_count -lt $max_retries ]; do
        if curl -sf "$api_url/health" > /dev/null 2>&1; then
            log_success "Rollback verified: health check passed"
            return 0
        fi
        
        retry_count=$((retry_count + 1))
        log_warning "Health check failed (attempt $retry_count/$max_retries)"
        sleep 10
    done
    
    log_error "Rollback verification failed"
    return 1
}

# Notify team
notify_team() {
    local environment=$1
    local status=$2
    local message=$3
    
    log "Notifying team of rollback..."
    
    # This would typically send a Slack message, email, or PagerDuty alert
    # For now, we'll just log it
    
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        local color="danger"
        if [ "$status" = "success" ]; then
            color="good"
        fi
        
        curl -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Deployment Rollback: $environment\",
                    \"text\": \"$message\",
                    \"ts\": $(date +%s)
                }]
            }"
    fi
}

# Main rollback function
perform_rollback() {
    local environment=$1
    local target_version=$2
    local api_url=$3
    
    log "Starting rollback for $environment..."
    
    # Determine target version if not specified
    if [ -z "$target_version" ]; then
        target_version=$(get_previous_version "$environment")
        if [ -z "$target_version" ]; then
            log_error "Could not determine previous version"
            return 1
        fi
        log "Using previous version: $target_version"
    fi
    
    # Perform environment-specific rollback
    case "$environment" in
        render)
            rollback_render "$target_version" || return 1
            ;;
        aws)
            rollback_aws "$target_version" || return 1
            ;;
        docker)
            rollback_docker "$target_version" || return 1
            ;;
        *)
            log_error "Unknown environment: $environment"
            return 1
            ;;
    esac
    
    # Verify rollback
    if verify_rollback "$environment" "$api_url"; then
        record_deployment "$environment" "$target_version" "success"
        notify_team "$environment" "success" "Rollback to $target_version completed successfully"
        log_success "Rollback completed successfully"
        return 0
    else
        record_deployment "$environment" "$target_version" "failed"
        notify_team "$environment" "failure" "Rollback to $target_version failed"
        log_error "Rollback failed"
        return 1
    fi
}

# Automatic rollback on deployment failure
auto_rollback_on_failure() {
    local environment=$1
    local api_url=$2
    
    log "Monitoring deployment for failures..."
    
    if ! detect_deployment_failure "$environment" "$api_url"; then
        log_warning "Deployment failure detected, initiating automatic rollback..."
        perform_rollback "$environment" "" "$api_url"
    fi
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -e, --environment ENV       Environment to rollback (render, aws, docker)
    -v, --version VERSION       Version to rollback to (optional, uses previous if not specified)
    -u, --api-url URL          API URL for health checks
    -a, --auto                 Automatic rollback on deployment failure
    -h, --help                 Show this help message

Examples:
    # Manual rollback to specific version
    $0 -e render -v v1.0.0 -u https://api.yourdomain.com

    # Automatic rollback on failure
    $0 -e aws -u https://api.yourdomain.com -a

    # Rollback to previous version
    $0 -e docker -u https://api.yourdomain.com
EOF
}

# Parse command line arguments
main() {
    local environment=""
    local version=""
    local api_url=""
    local auto_mode=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                environment="$2"
                shift 2
                ;;
            -v|--version)
                version="$2"
                shift 2
                ;;
            -u|--api-url)
                api_url="$2"
                shift 2
                ;;
            -a|--auto)
                auto_mode=true
                shift
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
    
    # Initialize
    init_deployment_history
    
    # Perform rollback
    if [ "$auto_mode" = true ]; then
        auto_rollback_on_failure "$environment" "$api_url"
    else
        perform_rollback "$environment" "$version" "$api_url"
    fi
}

# Run main function
main "$@"
