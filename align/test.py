        
        
    sa.stop_frequency = 11e6
    time.sleep(1)
    sa.center_frequency = 500e6
    sa.span = 2e6
    sa.reference_level = 3.

    sa.resolution_bandwidth = 1e3
    sa.sweep_time = 1.

    print(f"start={sa.start_frequency}")
    print(f"stop={sa.stop_frequency}")
    print(f"reference_level={sa.reference_level}")
    print(f"resolution_bandwidth={sa.resolution_bandwidth}")
    print(f"sweep_time={sa.sweep_time}")
    #print(f"frequency={sa.frequencies}")

    print(f"tracea={sa.trace_a}")
