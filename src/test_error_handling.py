from error_handling import PipelineErrorHandler, ErrorSeverity, ErrorType

print(' Testing Error Handling...')
handler = PipelineErrorHandler()

# Create a fake error to test
try:
    1/0  # This will cause a division by zero error
except Exception as e:
    handler.log_error(
        error=e, 
        severity=ErrorSeverity.HIGH, 
        error_type=ErrorType.DATA_VALIDATION, 
        context={'test': 'division by zero'}, 
        component='testing'
    )

print('Error handling test completed')
print('Error counts:', handler.error_counts)