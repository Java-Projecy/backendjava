package com.elecciones.backend.controller;

import com.elecciones.backend.model.VotoDistrital;
import com.elecciones.backend.service.VotoDistritalService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/data/district-votes")

public class VotoDistritalController {

    private final VotoDistritalService service;

    public VotoDistritalController(VotoDistritalService service) {
        this.service = service;
    }

    @GetMapping
    public List<VotoDistrital> getAll() {
        return service.getAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<VotoDistrital> getById(@PathVariable UUID id) {
        return service.getById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public VotoDistrital create(@RequestBody VotoDistrital voto) {
        return service.save(voto);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable UUID id) {
        service.delete(id);
    }
}
