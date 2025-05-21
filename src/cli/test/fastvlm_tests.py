#!/usr/bin/env python3
"""
FastVLM Test Module

This module provides test functions for FastVLM model functionality,
replacing the quick_test.sh script with a structured Python implementation.

The module is designed with a modular architecture where the main run_test function
coordinates the overall test flow while delegating specific test steps to specialized 
helper functions:

- prepare_test_environment: Sets up the test environment and parameters
- check_environment: Verifies the FastVLM environment is properly configured
- find_models: Discovers available FastVLM models or falls back to mock mode
- setup_sample_images: Prepares sample images for testing
- run_benchmarks: Executes benchmarks with either real or mock models
- test_analysis_modes: Tests different analysis modes with sample images

This modular approach improves maintainability, readability, and makes the code
easier to extend with new test capabilities.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

# Import model-related modules
from src.benchmark_fastvlm import download_test_images, find_test_images, run_benchmark
import src.fastvlm_analyzer
import src.fastvlm_errors

# Define a mock analyzer for testing without creating files
class MockAnalyzer:
    """Mock analyzer for testing without real FastVLM model."""
    def __init__(self):
        self.model_info = {'name': 'MockModel'}
        self.model_path = '/mock/path'
        
    def analyze_image(self, path, prompt=None, mode="describe"):
        """Simulate analyzing an image."""
        # Add slight delay to simulate processing
        time.sleep(0.1)
        
        if mode == "describe":
            return {
                "description": f"Mock analysis of image: {path}",
                "tags": ["test", "mock", "benchmark"],
                "metadata": {
                    "time": 0.1,
                    "model": "MockModel"
                }
            }
        elif mode == "detect":
            return {
                "objects": [
                    {"label": "mock object", "confidence": 0.95, "bbox": [10, 10, 100, 100]},
                    {"label": "test item", "confidence": 0.85, "bbox": [150, 150, 200, 200]}
                ],
                "metadata": {
                    "time": 0.1,
                    "model": "MockModel"
                }
            }
        elif mode == "document":
            return {
                "text": "This is mock extracted text from the document.",
                "document_type": "mock document",
                "metadata": {
                    "time": 0.1,
                    "model": "MockModel"
                }
            }
        else:
            return {
                "error": f"Unknown mode: {mode}",
                "metadata": {
                    "time": 0.1,
                    "model": "MockModel"
                }
            }

# Helper functions for run_test

def test_analysis_modes(test_env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test different analysis modes with a sample image.
    
    Args:
        test_env: Test environment dictionary
        
    Returns:
        Dictionary with mode testing results and any errors
    """
    # Extract required variables
    output_dir = test_env["output_dir"]
    logger = test_env["logger"]
    console = test_env["console"]
    model_size = test_env["model_size"]
    use_mock = test_env["use_mock"]
    test_image = test_env["test_image"]
    config = test_env["config"]
    sample_images = test_env.get("sample_images", [])
    
    # Initialize results
    results = {}
    errors = []
    
    if console:
        console.print(f"[blue]Testing with local image...[/blue]")
        
    try:
        # Use provided test image or default
        if test_image:
            test_img_path = test_image
        else:
            # Look for a test image in the standard locations
            test_data_dir = Path(config.runtime["project_root"]) / "test_data" / "images"
            test_img_candidates = [
                test_data_dir / "test.jpg",
                test_data_dir / "Layer 3 Merge.png",
                test_data_dir / "Untitled_4x.png"
            ]
            
            # Find first existing image
            test_img_path = None
            for img in test_img_candidates:
                if img.exists():
                    test_img_path = str(img)
                    break
                    
            # If no image found, use the first sample image
            if not test_img_path and sample_images:
                test_img_path = sample_images[0]
                
        if not test_img_path or not os.path.exists(test_img_path):
            logger.warning("No test image found")
            results["test_image"] = {
                "status": "warning",
                "message": "No test image found"
            }
            errors.append("No test image found")
        else:
            results["test_image"] = {
                "status": "ok",
                "message": f"Using test image: {test_img_path}",
                "path": test_img_path
            }
            
            # 8. Test different analysis modes with analyzer
            if console:
                console.print(f"[blue]Testing different analysis modes...[/blue]")
                
            try:
                # If using mock, use the built-in mock analyzer
                if use_mock:
                    analyzer = MockAnalyzer()
                else:
                    # Use real analyzer
                    analyzer = src.fastvlm_analyzer.FastVLMAnalyzer(model_size=model_size)
                    
                # Test different modes
                modes = ["describe", "detect", "document"]
                mode_results = {}
                
                for mode in modes:
                    try:
                        logger.info(f"Testing mode: {mode}")
                        result = analyzer.analyze_image(test_img_path, mode=mode)
                        
                        output_file = os.path.join(output_dir, f"{mode}_mode_result.txt")
                        with open(output_file, "w") as f:
                            if isinstance(result, dict):
                                json.dump(result, f, indent=2)
                            else:
                                f.write(str(result))
                                
                        mode_results[mode] = {
                            "status": "ok",
                            "message": f"Mode {mode} test completed",
                            "output_file": output_file
                        }
                    except Exception as e:
                        logger.error(f"Error testing mode {mode}: {e}")
                        mode_results[mode] = {
                            "status": "error",
                            "message": f"Error testing mode {mode}: {str(e)}"
                        }
                        errors.append(f"Mode {mode} test failed: {str(e)}")
                        
                results["analysis_modes"] = {
                    "status": "ok" if all(r.get("status") == "ok" for r in mode_results.values()) else "warning",
                    "message": "All modes tested successfully" if all(r.get("status") == "ok" for r in mode_results.values()) else "Some modes failed",
                    "modes": mode_results
                }
            except Exception as e:
                logger.error(f"Error testing analysis modes: {e}")
                results["analysis_modes"] = {
                    "status": "error",
                    "message": f"Error testing analysis modes: {str(e)}"
                }
                errors.append(f"Analysis modes test failed: {str(e)}")
    except Exception as e:
        logger.error(f"Error with test image: {e}")
        results["test_image"] = {
            "status": "error",
            "message": f"Error with test image: {str(e)}"
        }
        errors.append(f"Test image testing failed: {str(e)}")
        
    return {
        "results": results,
        "errors": errors
    }

def run_benchmarks(test_env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run benchmarks using either mock or real FastVLM model.
    
    Args:
        test_env: Test environment dictionary
        
    Returns:
        Dictionary with benchmark results and any errors
    """
    # Extract required variables
    output_dir = test_env["output_dir"]
    logger = test_env["logger"]
    console = test_env["console"]
    model_size = test_env["model_size"]
    use_mock = test_env["use_mock"]
    model_info = test_env.get("models", {}).get("model_info", {})
    
    # Initialize results
    results = {}
    errors = []
    
    # 5a. Run the mock benchmark with standard test images
    if use_mock:
        if console:
            console.print(f"[blue]Running benchmark with mock analyzer...[/blue]")
            
        try:
            # Use our built-in MockAnalyzer class
            mock_analyzer = MockAnalyzer()
            
            # Find test images
            image_files = find_test_images()
            
            if image_files:
                logger.info(f"Running benchmark with {len(image_files)} test images")
                output_file = os.path.join(output_dir, "mock_benchmark_results.json")
                benchmark_results = run_benchmark(mock_analyzer, image_files, output_file)
                
                results["mock_benchmark"] = {
                    "status": "ok",
                    "message": f"Mock benchmark completed with {len(image_files)} images",
                    "output_file": output_file,
                    "benchmark_results": benchmark_results
                }
            else:
                logger.warning("No test images found for testing")
                results["mock_benchmark"] = {
                    "status": "warning",
                    "message": "No test images found for testing"
                }
                errors.append("No test images found for benchmark")
                
        except Exception as e:
            logger.error(f"Error running mock benchmark: {e}")
            results["mock_benchmark"] = {
                "status": "error",
                "message": f"Error running mock benchmark: {str(e)}"
            }
            errors.append(f"Mock benchmark failed: {str(e)}")
    
    # 5b. Run the actual benchmark script (if model exists and not using mock)
    if not use_mock and model_info.get("available"):
        if console:
            console.print(f"[blue]Running actual benchmark with FastVLM model...[/blue]")
            
        try:
            # Run the benchmark directly
            from src.benchmark_fastvlm import main as benchmark_main
            
            # Redirect stdout/stderr temporarily to capture output
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            
            benchmark_output_file = os.path.join(output_dir, "benchmark.txt")
            
            try:
                with open(benchmark_output_file, "w") as f:
                    sys.stdout = f
                    sys.stderr = f
                    
                    # Run the benchmark with default arguments plus output file
                    benchmark_main(["--output", benchmark_output_file, "--size", model_size])
                    
                results["benchmark"] = {
                    "status": "ok",
                    "message": "Benchmark completed successfully",
                    "output_file": benchmark_output_file
                }
            except Exception as e:
                logger.warning(f"Benchmark failed: {e}")
                results["benchmark"] = {
                    "status": "warning",
                    "message": f"Benchmark failed: {str(e)}",
                    "output_file": benchmark_output_file
                }
                errors.append(f"Benchmark failed: {str(e)}")
            finally:
                # Restore stdout/stderr
                sys.stdout = original_stdout
                sys.stderr = original_stderr
                
        except Exception as e:
            logger.error(f"Error running benchmark: {e}")
            results["benchmark"] = {
                "status": "error",
                "message": f"Error running benchmark: {str(e)}"
            }
            errors.append(f"Benchmark failed: {str(e)}")
            
    return {
        "results": results,
        "errors": errors
    }

def setup_sample_images(test_env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Set up sample images for testing.
    
    Args:
        test_env: Test environment dictionary
        
    Returns:
        Dictionary with sample image setup results and any errors
    """
    # Extract required variables
    output_dir = test_env["output_dir"]
    logger = test_env["logger"]
    console = test_env["console"]
    config = test_env["config"]
    
    # Initialize results
    results = {}
    errors = []
    images = []
    
    if console:
        console.print(f"[blue]Using standard sample test images...[/blue]")
        
    try:
        # Ensure test data directory exists
        sample_dir = Path(config.runtime["project_root"]) / "test_data" / "sample_images"
        os.makedirs(sample_dir, exist_ok=True)
        
        # Download test images if needed
        images = download_test_images()
        
        # Save sample images log
        sample_images_log = os.path.join(output_dir, "sample_images_log.txt")
        with open(sample_images_log, "w") as f:
            f.write(f"Using {len(images)} sample test images in {os.path.abspath(sample_dir)}\n")
            for img in images:
                f.write(f"- {img}\n")
                
        results["sample_images"] = {
            "status": "ok",
            "message": f"Found {len(images)} sample test images",
            "images": images
        }
    except Exception as e:
        logger.error(f"Error with sample images: {e}")
        results["sample_images"] = {
            "status": "error",
            "message": f"Error with sample images: {str(e)}"
        }
        errors.append(f"Sample images setup failed: {str(e)}")
        
    return {
        "results": results,
        "errors": errors,
        "images": images
    }

def find_models(test_env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Find available FastVLM models.
    
    Args:
        test_env: Test environment dictionary
        
    Returns:
        Dictionary with model discovery results and any errors
    """
    # Extract required variables
    output_dir = test_env["output_dir"]
    logger = test_env["logger"]
    console = test_env["console"]
    model_size = test_env["model_size"]
    use_mock = test_env["use_mock"]
    config = test_env["config"]
    
    # Initialize results
    results = {}
    errors = []
    use_mock_result = use_mock
    
    if console:
        console.print(f"[blue]Looking for model files...[/blue]")
        
    try:
        # Check for model files
        model_info = config.get_model_info("fastvlm", model_size)
        
        # Save model files info
        model_files_path = os.path.join(output_dir, "model_files.txt")
        with open(model_files_path, "w") as f:
            f.write("Available models:\n")
            if model_info.get("available"):
                f.write(f"- {model_info['path']}\n")
                if "files" in model_info:
                    for file_info in model_info.get("files", []):
                        f.write(f"  - {file_info['name']} ({file_info['size_mb']:.2f} MB)\n")
            else:
                f.write("No models found\n")
                
        results["models"] = {
            "status": "ok" if model_info.get("available") else "warning",
            "message": "Model found" if model_info.get("available") else "No model found (will use mock)",
            "model_info": model_info
        }
        
        if not model_info.get("available") and not use_mock:
            logger.warning("No model found, tests will use mock model")
            use_mock_result = True
    except Exception as e:
        logger.error(f"Error finding models: {e}")
        results["models"] = {
            "status": "error",
            "message": f"Error finding models: {str(e)}"
        }
        errors.append(f"Model discovery failed: {str(e)}")
        use_mock_result = True
        
    return {
        "results": results,
        "errors": errors,
        "use_mock": use_mock_result
    }

def check_environment(test_env: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check the FastVLM environment for issues.
    
    Args:
        test_env: Test environment dictionary
        
    Returns:
        Dictionary with environment check results and any errors
    """
    # Extract required variables
    output_dir = test_env["output_dir"]
    logger = test_env["logger"]
    console = test_env["console"]
    
    # Initialize results
    results = {}
    errors = []
    
    if console:
        console.print(f"[blue]Checking environment...[/blue]")
        
    try:
        # Check environment using FastVLM error handler
        checker = src.fastvlm_analyzer.FastVLMAnalyzer()
        issues = []
        
        if src.fastvlm_errors.ERROR_HANDLER_AVAILABLE:
            issues = src.fastvlm_errors.FastVLMErrorHandler.check_environment()
            
        # Save environment check results
        env_check_file = os.path.join(output_dir, "environment_check.txt")
        with open(env_check_file, "w") as f:
            if not issues:
                f.write("Environment OK\n")
                results["environment"] = {
                    "status": "ok",
                    "message": "Environment check passed"
                }
            else:
                f.write(f"Environment issues found: {len(issues)}\n")
                for issue in issues:
                    f.write(f"- {issue}\n")
                results["environment"] = {
                    "status": "warning",
                    "message": f"Environment check found {len(issues)} issues",
                    "issues": issues
                }
                errors.append(f"Environment check found {len(issues)} issues")
    except Exception as e:
        logger.error(f"Error checking environment: {e}")
        results["environment"] = {
            "status": "error",
            "message": f"Error checking environment: {str(e)}"
        }
        errors.append(f"Environment check failed: {str(e)}")
        
    return {
        "results": results,
        "errors": errors
    }

def prepare_test_environment(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare the test environment by extracting context parameters
    and setting up the output directory.
    
    Args:
        context: Test context dictionary
        
    Returns:
        Dictionary with test setup details
    """
    # Extract test parameters from context
    name = context.get("name", "fastvlm")
    output_dir = context.get("output_dir")
    verbose = context.get("verbose", False)
    quiet = context.get("quiet", False)
    ci = context.get("ci", False)
    logger = context.get("logger", logging.getLogger("file-analyzer.test.fastvlm"))
    console = context.get("console")
    model_size = context.get("model_size", "0.5b")
    use_mock = context.get("use_mock", False)
    test_image = context.get("test_image")
    
    # Create output directory
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    else:
        # Use artifact system for output directory
        output_dir = context["config"].get_artifact_path("test", f"fastvlm_quick_test")
        os.makedirs(output_dir, exist_ok=True)
    
    # Print test information
    logger.info(f"Running FastVLM tests (mock: {use_mock}, size: {model_size})")
    logger.info(f"Output directory: {output_dir}")
    
    if console:
        console.print(f"[blue]Running FastVLM tests...[/blue]")
        console.print(f"[blue]Results will be saved to: {output_dir}[/blue]")
        
    # Return test setup details
    return {
        "name": name,
        "output_dir": output_dir,
        "verbose": verbose,
        "quiet": quiet,
        "ci": ci,
        "logger": logger,
        "console": console,
        "model_size": model_size,
        "use_mock": use_mock,
        "test_image": test_image,
        "config": context.get("config")
    }

def run_test(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run FastVLM model tests.
    
    This test verifies basic FastVLM functionality, including:
    - Environment setup and availability
    - Model file discovery
    - Basic image analysis
    - Different analysis modes
    
    Args:
        context: Test context dictionary
        
    Returns:
        Dictionary with test results
    """
    # Set up test environment
    test_env = prepare_test_environment(context)
    
    # Extract common variables for convenience
    output_dir = test_env["output_dir"]
    logger = test_env["logger"]
    console = test_env["console"]
    model_size = test_env["model_size"]
    use_mock = test_env["use_mock"]
    
    # Initialize results and errors tracking
    results = {}
    errors = []
    
    # 1. Run basic environment check
    check_result = check_environment(test_env)
    results.update(check_result["results"])
    errors.extend(check_result["errors"])
        
    # 2. Find available models
    model_result = find_models(test_env)
    results.update(model_result["results"])
    errors.extend(model_result["errors"])
    
    # Update use_mock flag based on model finding results
    if model_result.get("use_mock"):
        use_mock = True
        
    # 3. Use our built-in mock analyzer if needed
    if use_mock:
        if console:
            console.print(f"[blue]Using mock analyzer for testing...[/blue]")
            
        try:
            # Use our built-in MockAnalyzer class
            results["mock_analyzer"] = {
                "status": "ok",
                "message": "Using built-in MockAnalyzer class"
            }
        except Exception as e:
            logger.error(f"Error setting up mock analyzer: {e}")
            results["mock_analyzer"] = {
                "status": "error",
                "message": f"Error setting up mock analyzer: {str(e)}"
            }
            errors.append(f"Mock analyzer setup failed: {str(e)}")
            
    # 4. Use or download standard sample images
    sample_result = setup_sample_images(test_env)
    results.update(sample_result["results"])
    errors.extend(sample_result["errors"])
    
    # Update the test_env with image paths in case they're needed later
    if "images" in sample_result:
        test_env["sample_images"] = sample_result["images"]
        
    # 5. Run benchmarks (either mock or real)
    benchmark_result = run_benchmarks(test_env)
    results.update(benchmark_result["results"])
    errors.extend(benchmark_result["errors"])
            
    # 7. Test with standard local test image and run mode testing
    mode_test_result = test_analysis_modes(test_env)
    results.update(mode_test_result["results"])
    errors.extend(mode_test_result["errors"])
        
    # 9. Summarize tests
    if console:
        console.print(f"[green]All tests completed. Summary:[/green]")
        
    # Create summary
    summary_path = os.path.join(output_dir, "summary.txt")
    with open(summary_path, "w") as f:
        f.write("FastVLM Tests Summary:\n")
        f.write(f"Environment check: {results.get('environment', {}).get('status', 'unknown')}\n")
        f.write(f"Model files: {results.get('models', {}).get('status', 'unknown')}\n")
        f.write(f"Sample images: {results.get('sample_images', {}).get('message', 'unknown')}\n")
        f.write(f"Mock analyzer: {results.get('mock_analyzer', {}).get('status', 'not created')}\n")
        f.write(f"Benchmark: {results.get('benchmark', {}).get('status', 'not run')}\n")
        f.write(f"Test image: {results.get('test_image', {}).get('status', 'unknown')}\n")
        f.write(f"Analysis modes: {results.get('analysis_modes', {}).get('status', 'not tested')}\n")
        f.write(f"Errors: {len(errors)}\n")
        for i, error in enumerate(errors):
            f.write(f"  {i+1}. {error}\n")
            
    # Save full results as JSON
    results_path = os.path.join(output_dir, "test_results.json")
    with open(results_path, "w") as f:
        json.dump({
            "name": name,
            "timestamp": time.time(),
            "success": len(errors) == 0,
            "errors": errors,
            "results": results
        }, f, indent=2)
        
    # Ensure output directory is accessible
    # Note: Explicit permissions no longer set as os.makedirs creates with sufficient permissions
        
    # Return test results
    return {
        "success": len(errors) == 0,
        "message": "All tests passed" if len(errors) == 0 else f"{len(errors)} tests failed",
        "errors": errors,
        "output_dir": output_dir
    }

# Example test dictionary for registry
TESTS = {
    "basic": run_test,
    "mock": lambda context: run_test({**context, "use_mock": True}),
}

if __name__ == "__main__":
    # Simple test
    logger = logging.getLogger("file-analyzer")
    logger.setLevel(logging.INFO)
    result = run_test({
        "name": "fastvlm",
        "verbose": True,
        "use_mock": True,
        "logger": logger,
    })
    print(json.dumps(result, indent=2))